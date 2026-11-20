create table public.analyses (
  analysis_id text not null,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  created_at timestamptz not null,
  source_type text not null check (source_type in ('uploaded_csv', 'historical_replay')),
  filename text not null,
  model_version text not null,
  total_flows integer not null check (total_flows > 0),
  counts jsonb not null,
  payload jsonb not null,
  primary key (analysis_id, user_id)
);

create index analyses_owner_created on public.analyses (user_id, created_at desc, analysis_id desc);

create table public.analysis_flows (
  analysis_id text not null,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  row_id integer not null check (row_id > 0),
  features jsonb not null,
  primary key (analysis_id, user_id, row_id),
  foreign key (analysis_id, user_id) references public.analyses (analysis_id, user_id) on delete cascade
);

create table public.response_decisions (
  analysis_id text not null,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  row_id integer not null check (row_id > 0),
  decision text not null check (decision in ('simulated_block', 'dismissed')),
  decided_at timestamptz not null,
  primary key (analysis_id, user_id, row_id),
  foreign key (analysis_id, user_id) references public.analyses (analysis_id, user_id) on delete cascade
);

alter table public.analyses enable row level security;
alter table public.analyses force row level security;
alter table public.analysis_flows enable row level security;
alter table public.analysis_flows force row level security;
alter table public.response_decisions enable row level security;
alter table public.response_decisions force row level security;

create policy analyses_select_own on public.analyses for select to authenticated using ((select auth.uid()) = user_id);
create policy analyses_insert_own on public.analyses for insert to authenticated with check ((select auth.uid()) = user_id);
create policy analyses_update_own on public.analyses for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy analyses_delete_own on public.analyses for delete to authenticated using ((select auth.uid()) = user_id);

create policy analysis_flows_select_own on public.analysis_flows for select to authenticated using ((select auth.uid()) = user_id);
create policy analysis_flows_insert_own on public.analysis_flows for insert to authenticated with check ((select auth.uid()) = user_id);
create policy analysis_flows_update_own on public.analysis_flows for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy analysis_flows_delete_own on public.analysis_flows for delete to authenticated using ((select auth.uid()) = user_id);

create policy response_decisions_select_own on public.response_decisions for select to authenticated using ((select auth.uid()) = user_id);
create policy response_decisions_insert_own on public.response_decisions for insert to authenticated with check ((select auth.uid()) = user_id);
create policy response_decisions_update_own on public.response_decisions for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy response_decisions_delete_own on public.response_decisions for delete to authenticated using ((select auth.uid()) = user_id);

grant usage on schema public to authenticated;
grant select, insert, update, delete on public.analyses, public.analysis_flows, public.response_decisions to authenticated;

create or replace function public.save_analysis(p_payload jsonb, p_flows jsonb)
returns jsonb
language plpgsql
set search_path = ''
as $function$
begin
  if auth.uid() is null then
    raise exception 'Authentication required' using errcode = '42501';
  end if;
  if jsonb_typeof(p_payload) <> 'object' or jsonb_typeof(p_flows) <> 'array' then
    raise exception 'Invalid analysis payload' using errcode = '22023';
  end if;

  insert into public.analyses (
    analysis_id, created_at, source_type, filename, model_version, total_flows, counts, payload
  ) values (
    p_payload ->> 'analysis_id', (p_payload ->> 'created_at')::timestamptz,
    p_payload ->> 'source_type', p_payload ->> 'filename', p_payload ->> 'model_version',
    (p_payload ->> 'total_flows')::integer, p_payload -> 'counts', p_payload
  );

  insert into public.analysis_flows (analysis_id, row_id, features)
  select p_payload ->> 'analysis_id', ordinal::integer, value
  from jsonb_array_elements(p_flows) with ordinality as flow(value, ordinal);

  return p_payload;
end;
$function$;

revoke all on function public.save_analysis(jsonb, jsonb) from public, anon;
grant execute on function public.save_analysis(jsonb, jsonb) to authenticated;

create or replace function public.get_flow_prediction(p_analysis_id text, p_row_id integer)
returns jsonb
language sql
stable
set search_path = ''
as $function$
  select jsonb_build_object('prediction', a.payload -> 'predictions' -> (p_row_id - 1), 'features', f.features)
  from public.analyses as a
  left join public.analysis_flows as f
    on f.analysis_id = a.analysis_id and f.user_id = a.user_id and f.row_id = p_row_id
  where a.analysis_id = p_analysis_id
    and a.user_id = (select auth.uid())
    and p_row_id between 1 and a.total_flows;
$function$;

revoke all on function public.get_flow_prediction(text, integer) from public, anon;
grant execute on function public.get_flow_prediction(text, integer) to authenticated;
