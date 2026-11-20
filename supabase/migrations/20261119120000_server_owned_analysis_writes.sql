drop policy analyses_insert_own on public.analyses;
drop policy analyses_update_own on public.analyses;
drop policy analysis_flows_insert_own on public.analysis_flows;
drop policy analysis_flows_update_own on public.analysis_flows;
drop policy response_decisions_insert_own on public.response_decisions;
drop policy response_decisions_update_own on public.response_decisions;

revoke insert, update on public.analyses, public.analysis_flows, public.response_decisions from authenticated;
grant select, delete on public.analyses, public.analysis_flows, public.response_decisions to authenticated;
grant select, insert, update, delete on public.analyses, public.analysis_flows, public.response_decisions to service_role;
grant usage on schema public to authenticated, service_role;

revoke all on function public.save_analysis(jsonb, jsonb) from public, anon, authenticated;
drop function public.save_analysis(jsonb, jsonb);

create function public.save_analysis(p_user_id uuid, p_payload jsonb, p_flows jsonb)
returns jsonb
language plpgsql
set search_path = ''
as $function$
declare
  flow_count integer;
begin
  if p_user_id is null then
    raise exception 'User ID is required' using errcode = '22023';
  end if;
  if jsonb_typeof(p_payload) <> 'object' or jsonb_typeof(p_flows) <> 'array' then
    raise exception 'Invalid analysis payload' using errcode = '22023';
  end if;
  flow_count := jsonb_array_length(p_flows);
  if flow_count < 1 or flow_count > 10000 or (p_payload ->> 'total_flows')::integer <> flow_count then
    raise exception 'Invalid flow count' using errcode = '22023';
  end if;

  insert into public.analyses (
    analysis_id, user_id, created_at, source_type, filename, model_version, total_flows, counts, payload
  ) values (
    p_payload ->> 'analysis_id', p_user_id, (p_payload ->> 'created_at')::timestamptz,
    p_payload ->> 'source_type', p_payload ->> 'filename', p_payload ->> 'model_version',
    flow_count, p_payload -> 'counts', p_payload
  );

  insert into public.analysis_flows (analysis_id, user_id, row_id, features)
  select p_payload ->> 'analysis_id', p_user_id, ordinal::integer, value
  from jsonb_array_elements(p_flows) with ordinality as flow(value, ordinal);

  return p_payload;
end;
$function$;

revoke all on function public.save_analysis(uuid, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.save_analysis(uuid, jsonb, jsonb) to service_role;
