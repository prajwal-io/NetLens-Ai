-- RLS filters rows but does not constrain TRUNCATE, so reset table ACLs first.
revoke all privileges on table
  public.analyses,
  public.analysis_flows,
  public.response_decisions
from public, anon, authenticated, service_role;

drop policy if exists analysis_flows_delete_own on public.analysis_flows;

grant select, delete on table public.analyses, public.response_decisions to authenticated;
grant select on table public.analysis_flows to authenticated;
grant select, insert, update, delete on table
  public.analyses,
  public.analysis_flows,
  public.response_decisions
to service_role;

grant usage on schema public to authenticated, service_role;
