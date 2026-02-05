#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild Annoy Vector Index - ABU System
Converts solidified Brooks patterns to 32-dim vectors and builds Annoy index
"""

import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from annoy import AnnoyIndex

    from abu.unified_vectorizer import UnifiedVectorizer
    from db_manager_trader import TraderDBManager

    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)


class VectorIndexBuilder:
    """Build Annoy index from solidified Brooks patterns"""

    def __init__(self, trader_id: str = "abu", dim: int = 32):
        if not DB_AVAILABLE:
            raise RuntimeError("Dependencies not available")

        self.trader_id = trader_id
        self.dim = dim
        self.db = TraderDBManager(trader_id)
        self.vectorizer = UnifiedVectorizer()
        self.index = AnnoyIndex(dim, "angular")
        self.id_map = {}  # annoy_idx -> pattern_vector_id

    def load_and_vectorize(self) -> int:
        """Load patterns from DB and convert to 32-dim vectors"""
        print("\n" + "=" * 80)
        print("LOADING PATTERNS FROM DATABASE")
        print("=" * 80)

        conn = self.db._get_connection()

        try:
            rows = conn.execute("""
                SELECT id, pattern_features, market_context, metadata
                FROM pattern_vectors
                ORDER BY id
            """).fetchall()

            total = len(rows)
            print(f"\nLoaded {total} patterns")

            print("\n" + "=" * 80)
            print("VECTORIZING PATTERNS")
            print("=" * 80)

            for annoy_idx, row in enumerate(rows):
                vec_id = row[0]
                pf = row[1] or {}
                mc = row[2] or {}
                meta = row[3] or {}

                # Convert to 32-dim vector
                vec = self.vectorizer.vectorize_brooks_pattern(pf, mc, meta)

                # Add to Annoy index
                self.index.add_item(annoy_idx, vec)
                self.id_map[annoy_idx] = vec_id

                if (annoy_idx + 1) % 100 == 0:
                    print(f"  Vectorized {annoy_idx + 1}/{total} patterns...")

            print(f"\n✓ Vectorized {total} patterns")
            return total

        finally:
            conn.close()

    def build_index(self, n_trees: int = 10) -> None:
        """Build Annoy index with specified number of trees"""
        print("\n" + "=" * 80)
        print(f"BUILDING ANNOY INDEX ({n_trees} trees)")
        print("=" * 80)

        self.index.build(n_trees)
        print(f"\n✓ Index built with {n_trees} trees")

    def save_index(self, output_path: Path) -> None:
        """Save Annoy index and ID mapping"""
        print("\n" + "=" * 80)
        print("SAVING INDEX")
        print("=" * 80)

        # Save Annoy index
        index_file = output_path / "brooks_patterns_32d.ann"
        self.index.save(str(index_file))
        print(f"  Saved Annoy index: {index_file}")

        # Save ID mapping
        import json

        map_file = output_path / "brooks_patterns_id_map.json"
        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(self.id_map, f, indent=2)
        print(f"  Saved ID mapping: {map_file}")

        print(f"\n✓ Index saved to {output_path}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Rebuild Annoy vector index from solidified Brooks patterns"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/vectors",
        help="Output directory for index files",
    )
    parser.add_argument(
        "--trees",
        type=int,
        default=10,
        help="Number of trees for Annoy index (default: 10)",
    )

    args = parser.parse_args()

    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build index
    builder = VectorIndexBuilder(trader_id="abu", dim=32)
    total = builder.load_and_vectorize()
    builder.build_index(n_trees=args.trees)
    builder.save_index(output_path)

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
    print(f"Total patterns indexed: {total}")
    print(f"Index dimension: 32")
    print(f"Number of trees: {args.trees}")


if __name__ == "__main__":
    main()
