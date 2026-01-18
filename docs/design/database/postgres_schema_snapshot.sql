-- Postgres schema snapshot (public schema)
-- Generated from live database

-- Table: public.klines
CREATE TABLE public.klines (
    timestamp bigint NOT NULL,
    exchange text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    open double precision NOT NULL,
    high double precision NOT NULL,
    low double precision NOT NULL,
    close double precision NOT NULL,
    volume double precision NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Constraints for public.klines
ALTER TABLE ONLY public.klines ADD CONSTRAINT klines_pkey PRIMARY KEY ("timestamp", exchange, symbol, timeframe);

-- Indexes for public.klines
CREATE INDEX idx_klines_exchange_symbol_tf ON public.klines USING btree (exchange, symbol, timeframe);
CREATE INDEX idx_klines_symbol_tf ON public.klines USING btree (symbol, timeframe);
CREATE INDEX idx_klines_timestamp ON public.klines USING btree ("timestamp");

-- Table: public.ml_optimization_results
CREATE TABLE public.ml_optimization_results (
    id integer DEFAULT nextval('ml_optimization_results_id_seq'::regclass) NOT NULL,
    model_type character varying(50),
    parameters_json text,
    metrics_json text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

-- Constraints for public.ml_optimization_results
ALTER TABLE ONLY public.ml_optimization_results ADD CONSTRAINT ml_optimization_results_pkey PRIMARY KEY (id);

-- Indexes for public.ml_optimization_results
CREATE INDEX idx_ml_model_type ON public.ml_optimization_results USING btree (model_type);

-- Table: public.pattern_library
CREATE TABLE public.pattern_library (
    id integer DEFAULT nextval('pattern_library_id_seq'::regclass) NOT NULL,
    pattern_name text,
    pattern_type text,
    confidence numeric(5,2),
    chart_path text,
    gemini_annotation_json text,
    chart_features_json text,
    ebook_references text,
    text_description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    source_page integer,
    source_pdf text,
    image_path text,
    context_text text,
    timeframe_hint text,
    direction text,
    key_features text,
    updated_at timestamp without time zone
);

-- Constraints for public.pattern_library
ALTER TABLE ONLY public.pattern_library ADD CONSTRAINT pattern_library_pkey PRIMARY KEY (id);

-- Indexes for public.pattern_library
CREATE INDEX idx_pattern_name ON public.pattern_library USING btree (pattern_name);
CREATE INDEX idx_pattern_source_page ON public.pattern_library USING btree (source_page);
CREATE INDEX idx_pattern_type ON public.pattern_library USING btree (pattern_type);

-- Table: public.signal_evaluations
CREATE TABLE public.signal_evaluations (
    id integer DEFAULT nextval('signal_evaluations_id_seq'::regclass) NOT NULL,
    signal_id integer NOT NULL,
    evaluation_time timestamp without time zone NOT NULL,
    result character varying(20),
    actual_entry_price numeric(20,8),
    actual_exit_price numeric(20,8),
    actual_profit_pct numeric(10,4),
    actual_profit_usdt numeric(20,8),
    stop_loss_hit boolean DEFAULT false,
    take_profit_1_hit boolean DEFAULT false,
    take_profit_2_hit boolean DEFAULT false,
    missed boolean DEFAULT false,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

-- Constraints for public.signal_evaluations
ALTER TABLE ONLY public.signal_evaluations ADD CONSTRAINT signal_evaluations_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.signal_evaluations ADD CONSTRAINT signal_evaluations_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES trading_signals(id) ON DELETE CASCADE;

-- Indexes for public.signal_evaluations
CREATE INDEX idx_evaluations_signal_id ON public.signal_evaluations USING btree (signal_id);
CREATE INDEX idx_evaluations_time ON public.signal_evaluations USING btree (evaluation_time);

-- Table: public.system_configs
CREATE TABLE public.system_configs (
    id integer DEFAULT nextval('system_configs_id_seq'::regclass) NOT NULL,
    config_key character varying(100) NOT NULL,
    config_value text,
    description text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

-- Constraints for public.system_configs
ALTER TABLE ONLY public.system_configs ADD CONSTRAINT system_configs_config_key_key UNIQUE (config_key);
ALTER TABLE ONLY public.system_configs ADD CONSTRAINT system_configs_pkey PRIMARY KEY (id);

-- Indexes for public.system_configs
CREATE INDEX idx_config_key ON public.system_configs USING btree (config_key);
CREATE UNIQUE INDEX system_configs_config_key_key ON public.system_configs USING btree (config_key);

-- Table: public.trading_signals
CREATE TABLE public.trading_signals (
    id integer DEFAULT nextval('trading_signals_id_seq'::regclass) NOT NULL,
    signal_time timestamp without time zone NOT NULL,
    timeframe character varying(10),
    symbol character varying(20),
    signal_type character varying(10),
    entry_price numeric(20,8),
    stop_loss numeric(20,8),
    take_profit_1 numeric(20,8),
    take_profit_2 numeric(20,8),
    entry_model text,
    strength character varying(20),
    risk_reward_ratio numeric(10,2),
    volatility_level character varying(20),
    system_name character varying(50),
    score numeric(10,2),
    notes text,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone,
    entry_time timestamp without time zone,
    exit_time timestamp without time zone,
    exit_price numeric(20,8),
    exit_reason text,
    pnl_pct numeric(10,4),
    breakeven_stop_set boolean DEFAULT false,
    quick_tp_reached boolean DEFAULT false,
    last_check_time timestamp without time zone,
    check_count integer DEFAULT 0,
    entry_price_actual numeric(20,8)
);

-- Constraints for public.trading_signals
ALTER TABLE ONLY public.trading_signals ADD CONSTRAINT trading_signals_pkey PRIMARY KEY (id);

-- Indexes for public.trading_signals
CREATE INDEX idx_signals_created_at ON public.trading_signals USING btree (created_at);
CREATE INDEX idx_signals_status ON public.trading_signals USING btree (status);
CREATE INDEX idx_signals_symbol ON public.trading_signals USING btree (symbol);
CREATE INDEX idx_signals_system ON public.trading_signals USING btree (system_name);
CREATE INDEX idx_signals_timeframe ON public.trading_signals USING btree (timeframe);

