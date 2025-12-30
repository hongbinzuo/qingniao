#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X (Twitter) 推文下载工具
支持多种下载方式，自动选择最可用的方法
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class TwitterDownloader:
    """X (Twitter) 推文下载器"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化下载器
        
        Args:
            output_dir: 输出目录，默认为 data/twitter_tweets
        """
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent.parent / "data" / "twitter_tweets"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 尝试导入各种库
        self.twscrape_available = False
        self.twitter_scraper_available = False
        self.selenium_available = False
        
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查可用的依赖库"""
        # 检查 twscrape
        try:
            import twscrape
            self.twscrape_available = True
            print("✓ twscrape 可用")
        except ImportError:
            pass
        
        # 检查 twitter-scraper (n0madic)
        try:
            from twitter_scraper import TwitterScraper
            self.twitter_scraper_available = True
            print("✓ twitter-scraper 可用")
        except ImportError:
            pass
        
        # 检查 selenium
        try:
            from selenium import webdriver
            self.selenium_available = True
            print("✓ selenium 可用")
        except ImportError:
            pass
        
        if not any([self.twscrape_available, self.twitter_scraper_available, self.selenium_available]):
            print("⚠️  未找到可用的下载库")
            print("\n推荐安装以下工具之一：")
            print("1. twscrape: pip install twscrape")
            print("2. twitter-scraper: pip install twitter-scraper")
            print("3. selenium: pip install selenium")
    
    def download_user_tweets_twscrape(self, username: str, limit: int = 100) -> List[Dict]:
        """
        使用 twscrape 下载用户推文
        
        Args:
            username: 用户名（不含@）
            limit: 下载数量限制
            
        Returns:
            推文列表
        """
        if not self.twscrape_available:
            raise ImportError("twscrape 未安装，请运行: pip install twscrape")
        
        try:
            import twscrape
            import asyncio
            
            async def fetch_tweets():
                api = twscrape.API()
                tweets = []
                
                async for tweet in api.user_tweets(username, limit=limit):
                    tweets.append({
                        'id': tweet.id,
                        'text': tweet.rawContent,
                        'created_at': tweet.date.isoformat() if tweet.date else None,
                        'likes': tweet.likeCount,
                        'retweets': tweet.retweetCount,
                        'replies': tweet.replyCount,
                        'url': f"https://twitter.com/{username}/status/{tweet.id}",
                        'username': username
                    })
                
                return tweets
            
            return asyncio.run(fetch_tweets())
            
        except Exception as e:
            print(f"✗ twscrape 下载失败: {e}")
            return []
    
    def download_user_tweets_twitter_scraper(self, username: str, limit: int = 100) -> List[Dict]:
        """
        使用 twitter-scraper 下载用户推文
        
        Args:
            username: 用户名（不含@）
            limit: 下载数量限制
            
        Returns:
            推文列表
        """
        if not self.twitter_scraper_available:
            raise ImportError("twitter-scraper 未安装，请运行: pip install twitter-scraper")
        
        try:
            from twitter_scraper import TwitterScraper
            
            scraper = TwitterScraper()
            tweets = []
            
            # 注意：twitter-scraper 的API可能已变化，需要根据实际版本调整
            for tweet in scraper.get_tweets(username, limit=limit):
                tweets.append({
                    'id': tweet.get('id'),
                    'text': tweet.get('text', ''),
                    'created_at': tweet.get('created_at'),
                    'likes': tweet.get('likes', 0),
                    'retweets': tweet.get('retweets', 0),
                    'replies': tweet.get('replies', 0),
                    'url': tweet.get('url', ''),
                    'username': username
                })
            
            return tweets
            
        except Exception as e:
            print(f"✗ twitter-scraper 下载失败: {e}")
            return []
    
    def download_user_tweets_selenium(self, username: str, limit: int = 100) -> List[Dict]:
        """
        使用 Selenium 下载用户推文（需要登录）
        
        Args:
            username: 用户名（不含@）
            limit: 下载数量限制
            
        Returns:
            推文列表
        """
        if not self.selenium_available:
            raise ImportError("selenium 未安装，请运行: pip install selenium")
        
        print("⚠️  Selenium 方法需要浏览器驱动和登录，实现较复杂")
        print("   建议使用 twscrape 或 twitter-scraper")
        return []
    
    def download_user_tweets(self, username: str, limit: int = 100, method: Optional[str] = None) -> List[Dict]:
        """
        下载用户推文（自动选择最佳方法）
        
        Args:
            username: 用户名（不含@）
            limit: 下载数量限制
            method: 指定方法 ('twscrape', 'twitter_scraper', 'selenium')，None为自动选择
            
        Returns:
            推文列表
        """
        username = username.lstrip('@')
        
        # 自动选择方法
        if method is None:
            if self.twscrape_available:
                method = 'twscrape'
            elif self.twitter_scraper_available:
                method = 'twitter_scraper'
            elif self.selenium_available:
                method = 'selenium'
            else:
                raise RuntimeError("没有可用的下载方法，请先安装依赖库")
        
        print(f"使用 {method} 方法下载 @{username} 的推文...")
        
        if method == 'twscrape':
            tweets = self.download_user_tweets_twscrape(username, limit)
        elif method == 'twitter_scraper':
            tweets = self.download_user_tweets_twitter_scraper(username, limit)
        elif method == 'selenium':
            tweets = self.download_user_tweets_selenium(username, limit)
        else:
            raise ValueError(f"未知方法: {method}")
        
        return tweets
    
    def save_tweets(self, tweets: List[Dict], filename: Optional[str] = None):
        """
        保存推文到文件
        
        Args:
            tweets: 推文列表
            filename: 文件名，默认为 tweets_用户名_时间戳.json
        """
        if not tweets:
            print("没有推文可保存")
            return
        
        if filename is None:
            username = tweets[0].get('username', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"tweets_{username}_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已保存 {len(tweets)} 条推文到: {filepath}")
    
    def download_and_save(self, username: str, limit: int = 100, method: Optional[str] = None):
        """
        下载并保存推文
        
        Args:
            username: 用户名（不含@）
            limit: 下载数量限制
            method: 指定方法，None为自动选择
        """
        tweets = self.download_user_tweets(username, limit, method)
        if tweets:
            self.save_tweets(tweets)


def main():
    """主函数"""
    print("=" * 80)
    print("X (Twitter) 推文下载工具")
    print("=" * 80)
    print()
    
    downloader = TwitterDownloader()
    
    # 示例：下载推文
    if len(sys.argv) > 1:
        username = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        
        print(f"下载 @{username} 的 {limit} 条推文...")
        downloader.download_and_save(username, limit)
    else:
        print("使用方法:")
        print("  python twitter_downloader.py <username> [limit]")
        print()
        print("示例:")
        print("  python twitter_downloader.py elonmusk 50")
        print()
        print("注意:")
        print("  1. 需要先安装依赖库:")
        print("     pip install twscrape")
        print("     或")
        print("     pip install twitter-scraper")
        print()
        print("  2. twscrape 需要先添加账号:")
        print("     twscrape add_accounts accounts.txt username:password:email:email_password")
        print("     或使用 cookie 登录")


if __name__ == '__main__':
    main()


