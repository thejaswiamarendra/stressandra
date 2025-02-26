import pytest
from stressandra.jmx import collect_metrics

@pytest.fixture
def mock_jmxquery(mocker):
    mock_connection = mocker.patch("stressandra.jmx.JMXConnection")
    mock_query = mocker.patch("stressandra.jmx.JMXQuery")

    # Simulated JMX query results
    mock_connection().query.return_value = [
        mocker.Mock(metric_name="ClientRequest.Write.Latency", value=2.5),
        mocker.Mock(metric_name="ClientRequest.Read.Latency", value=1.2),
        mocker.Mock(metric_name="Storage.Load", value=1000),
    ]

    return mock_connection

def test_collect_metrics(mock_jmxquery):
    results = collect_metrics(jmx_port=7199)

    # Validate expected metrics are present
    assert any(m.metric_name == "ClientRequest.Write.Latency" and m.value == 2.5 for m in results)
    assert any(m.metric_name == "ClientRequest.Read.Latency" and m.value == 1.2 for m in results)
    assert any(m.metric_name == "Storage.Load" and m.value == 1000 for m in results)

    # Ensure query() was called once
    mock_jmxquery().query.assert_called_once()
