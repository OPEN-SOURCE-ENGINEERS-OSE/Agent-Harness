create table public.research_turns (
  id uuid primary key,
  session_id uuid not null,
  thread_id uuid not null,
  question text not null,
  answer text not null,
  sources jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
create index research_turns_session_time on public.research_turns (session_id, created_at desc);
alter table public.research_turns enable row level security;
revoke all on public.research_turns from anon, authenticated;
grant select, insert on public.research_turns to service_role;
