create table if not exists public.daily_runs (
  id bigserial primary key,
  generated_at timestamptz not null,
  source text not null default 'question-forecast',
  top_count integer not null default 0,
  cabinet_high_count integer not null default 0,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  unique (generated_at, source)
);

create table if not exists public.issue_packets (
  id bigserial primary key,
  run_id bigint not null references public.daily_runs(id) on delete cascade,
  rank integer not null,
  issue_id text not null,
  ministry text not null,
  likelihood_score numeric,
  likelihood_band text,
  priority numeric,
  article_count integer,
  diagnosis text,
  first_question text,
  answer_frame text,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  unique (run_id, issue_id)
);

create table if not exists public.question_feedback (
  id bigserial primary key,
  issue_packet_id bigint references public.issue_packets(id) on delete cascade,
  issue_id text not null,
  feedback text not null check (feedback in ('hit','near','miss','irrelevant','needs_evidence')),
  note text,
  created_at timestamptz not null default now()
);

create index if not exists issue_packets_issue_idx on public.issue_packets(issue_id);
create index if not exists issue_packets_ministry_idx on public.issue_packets(ministry);
create index if not exists issue_packets_band_idx on public.issue_packets(likelihood_band);
create index if not exists issue_packets_payload_gin on public.issue_packets using gin(payload);
