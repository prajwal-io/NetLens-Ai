BEGIN;
SELECT plan(15);

SELECT ok((
  SELECT bool_and(c.relrowsecurity AND c.relforcerowsecurity)
  FROM pg_class AS c
  JOIN pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname IN ('analyses', 'analysis_flows', 'response_decisions')
), 'all user-data tables force row-level security');

SELECT ok(has_table_privilege('authenticated', 'public.analyses', 'select'), 'users can read their analysis rows');
SELECT ok(has_table_privilege('authenticated', 'public.analysis_flows', 'select'), 'users can read their own flow rows under RLS');
SELECT ok(has_table_privilege('authenticated', 'public.response_decisions', 'select'), 'users can read their response decisions');

SELECT ok((
  NOT has_table_privilege('authenticated', 'public.analyses', 'insert')
  AND NOT has_table_privilege('authenticated', 'public.analyses', 'update')
  AND NOT has_table_privilege('authenticated', 'public.analyses', 'truncate')
), 'users cannot write or truncate analyses directly');
SELECT ok((
  NOT has_table_privilege('authenticated', 'public.analysis_flows', 'insert')
  AND NOT has_table_privilege('authenticated', 'public.analysis_flows', 'update')
  AND NOT has_table_privilege('authenticated', 'public.analysis_flows', 'delete')
  AND NOT has_table_privilege('authenticated', 'public.analysis_flows', 'truncate')
), 'users cannot write or truncate flow rows directly');
SELECT ok((
  NOT has_table_privilege('authenticated', 'public.response_decisions', 'insert')
  AND NOT has_table_privilege('authenticated', 'public.response_decisions', 'update')
  AND NOT has_table_privilege('authenticated', 'public.response_decisions', 'truncate')
), 'users cannot write or truncate response decisions directly');

SELECT ok((
  NOT has_table_privilege('anon', 'public.analyses', 'select')
  AND NOT has_table_privilege('anon', 'public.analyses', 'insert')
  AND NOT has_table_privilege('anon', 'public.analyses', 'truncate')
), 'anonymous clients cannot access analyses');
SELECT ok((
  NOT has_table_privilege('anon', 'public.analysis_flows', 'select')
  AND NOT has_table_privilege('anon', 'public.analysis_flows', 'insert')
  AND NOT has_table_privilege('anon', 'public.analysis_flows', 'truncate')
), 'anonymous clients cannot access flow rows');
SELECT ok((
  NOT has_table_privilege('anon', 'public.response_decisions', 'select')
  AND NOT has_table_privilege('anon', 'public.response_decisions', 'insert')
  AND NOT has_table_privilege('anon', 'public.response_decisions', 'truncate')
), 'anonymous clients cannot access response decisions');

SELECT is((
  SELECT count(*)::integer
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('analyses', 'analysis_flows', 'response_decisions')
    AND cmd = 'SELECT'
    AND roles::text LIKE '%authenticated%'
    AND coalesce(qual, '') ILIKE '%auth.uid()%'
    AND coalesce(qual, '') ILIKE '%user_id%'
), 3, 'each table has an owner-scoped read policy');
SELECT is((
  SELECT count(*)::integer
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('analyses', 'analysis_flows', 'response_decisions')
    AND cmd = 'DELETE'
    AND roles::text LIKE '%authenticated%'
    AND coalesce(qual, '') ILIKE '%auth.uid()%'
    AND coalesce(qual, '') ILIKE '%user_id%'
), 2, 'only deletable user records have owner-scoped delete policies');
SELECT is((
  SELECT count(*)::integer
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('analyses', 'analysis_flows', 'response_decisions')
    AND cmd IN ('INSERT', 'UPDATE')
    AND roles::text LIKE '%authenticated%'
), 0, 'authenticated users have no direct write policies');

SELECT ok((
  has_table_privilege('service_role', 'public.analyses', 'insert')
  AND has_table_privilege('service_role', 'public.analysis_flows', 'insert')
  AND has_table_privilege('service_role', 'public.response_decisions', 'insert')
  AND has_table_privilege('service_role', 'public.response_decisions', 'update')
), 'the backend-only service role can perform validated writes');
SELECT ok((
  has_function_privilege('service_role', 'public.save_analysis(uuid,jsonb,jsonb)', 'execute')
  AND NOT has_function_privilege('authenticated', 'public.save_analysis(uuid,jsonb,jsonb)', 'execute')
  AND NOT has_function_privilege('anon', 'public.save_analysis(uuid,jsonb,jsonb)', 'execute')
  AND has_function_privilege('authenticated', 'public.get_flow_prediction(text,integer)', 'execute')
  AND NOT has_function_privilege('anon', 'public.get_flow_prediction(text,integer)', 'execute')
), 'analysis writes are server-only and flow reads require authentication');

SELECT * FROM finish();
ROLLBACK;
