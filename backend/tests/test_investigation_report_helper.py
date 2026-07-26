"""
Unit tests for InvestigationService _is_investigation_report_request and investigation pipeline.
"""
import pytest
from unittest.mock import MagicMock

from backend.ai.services.investigation_service import InvestigationService


def test_is_investigation_report_request_detection():
    service = InvestigationService(
        session=MagicMock(),
        chat_service=MagicMock(),
        intent_service=MagicMock(),
        sql_generation_service=MagicMock(),
        sql_validation_service=MagicMock(),
        ai_query_service=MagicMock(),
    )

    # 1. Investigation report queries (count + location/time or details)
    report_query_1 = "How many theft cases in Mysuru during last 30 days?"
    report_query_2 = "Count of robbery cases in Bengaluru with solved and pending statistics"

    assert service._is_investigation_report_request(report_query_1) is True
    assert service._is_investigation_report_query(report_query_1) is True
    assert service._is_investigation_report_request(report_query_2) is True

    # 2. Normal non-report investigation queries
    normal_query_1 = "What is the status of FIR/2026/012?"
    normal_query_2 = "Who is the investigating officer for case 5?"

    assert service._is_investigation_report_request(normal_query_1) is False
    assert service._is_investigation_report_request(normal_query_2) is False


def test_investigate_does_not_raise_attribute_error_on_missing_helper():
    mock_intent = MagicMock()
    mock_intent_obj = MagicMock()
    from backend.ai.schemas.ai import Intent
    mock_intent_obj.intent = Intent.CASE_SEARCH
    mock_intent.classify.return_value = mock_intent_obj

    mock_case_svc = MagicMock()
    mock_case_svc.list_cases.return_value = ([], 0)

    service = InvestigationService(
        session=MagicMock(),
        chat_service=MagicMock(),
        intent_service=mock_intent,
        sql_generation_service=MagicMock(),
        sql_validation_service=MagicMock(),
        ai_query_service=MagicMock(),
        case_service=mock_case_svc,
    )

    # Verify that calling investigate with a standard query does NOT raise AttributeError
    try:
        service.investigate("Show recent theft cases", request_id="req-123")
    except AttributeError as exc:
        pytest.fail(f"investigate() raised AttributeError: {exc}")
    except Exception:
        # Other pipeline steps might mock or fail, but AttributeError must NOT occur
        pass


def test_analytics_service_resolve_district_string_handling():
    from backend.services.analytics_service import AnalyticsService, DistrictRef
    mock_session = MagicMock()
    mock_session.execute.return_value.first.return_value = (1,)
    svc = AnalyticsService(mock_session)

    # Verify passing string "Mysuru" does not raise AttributeError
    res_str = svc._resolve_district_id("Mysuru")
    assert res_str == 1

    res_ref = svc._resolve_district_id(DistrictRef(name="Mysuru"))
    assert res_ref == 1


def test_investigation_report_fallback_calls_session_rollback():
    mock_session = MagicMock()
    mock_chat = MagicMock()
    mock_chat.chat_with_prompt.return_value.content = '{"headline": "Report", "summary": "Test"}'
    
    mock_sql_gen = MagicMock()
    mock_sql_val = MagicMock()
    mock_ai_query = MagicMock()
    
    from backend.ai.services.exceptions import ExecutionFailure
    mock_ai_query.execute_validated_sql.side_effect = ExecutionFailure("InFailedSqlTransaction error")

    mock_case_svc = MagicMock()
    mock_case_svc.list_cases.return_value = ([], 0)

    service = InvestigationService(
        session=mock_session,
        chat_service=mock_chat,
        intent_service=MagicMock(),
        sql_generation_service=mock_sql_gen,
        sql_validation_service=mock_sql_val,
        ai_query_service=mock_ai_query,
        case_service=mock_case_svc,
    )

    resp = service._handle_investigation_report_request(
        question="How many theft cases in Mysuru during last 7 days?",
        request_id="req-rollback-test",
        metadata=None,
    )

    # Verify session rollback was invoked
    mock_session.rollback.assert_called()
    assert resp.request_id == "req-rollback-test"


