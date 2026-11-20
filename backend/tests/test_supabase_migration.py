from pathlib import Path


def test_analysis_writes_are_granted_only_to_server_role():
    migration = (Path(__file__).resolve().parents[2] / "supabase" / "migrations" /
                 "20261119120000_server_owned_analysis_writes.sql").read_text(encoding="utf-8").lower()
    assert "revoke insert, update on public.analyses, public.analysis_flows, public.response_decisions from authenticated" in migration
    assert "grant select, delete on public.analyses, public.analysis_flows, public.response_decisions to authenticated" in migration
    assert "grant execute on function public.save_analysis(uuid, jsonb, jsonb) to service_role" in migration
    assert "grant execute on function public.save_analysis(uuid, jsonb, jsonb) to authenticated" not in migration
    assert "auth.role()" not in migration


def test_analysis_tables_enforce_authenticated_owner_rls():
    migration = (Path(__file__).resolve().parents[2] / "supabase" / "migrations" /
                 "20261118120000_create_user_owned_analyses.sql").read_text(encoding="utf-8").lower()
    for table in ("analyses", "analysis_flows", "response_decisions"):
        assert f"alter table public.{table} enable row level security" in migration
        assert f"alter table public.{table} force row level security" in migration
        assert f"on public.{table} for select to authenticated using ((select auth.uid()) = user_id)" in migration
        assert f"on public.{table} for insert to authenticated with check ((select auth.uid()) = user_id)" in migration
