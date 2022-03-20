"""
Test ConsoleParser module

"""

import pytest
from unittest.mock import patch

from ..sample.console_parser import ConsoleParser, Response


EMPTY_CONSOLE_OUTPUT = """'Elastic KibanaDDev ToolsExpandRecently viewedDiscoverVisualizeDashboardCanvasMapsMachine LearningMetricsLogsAPMUptimeSIEMDev ToolsStack MonitoringManagement\n\nConsoleSearch ProfilerGrok DebuggerPainless LabBetaConsoleHistorySettingsHelpDev Tools ConsolePress Enter to start editing.When you’re done, press Escape to stop editing.123456GET _search{ "query": {  "match_all": {} }}XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXDev Tools Console output1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n'"""
QUERY_EXAMPLE = {
    "size": 1,
    "query": {
        "match": {
            "message": "*fdbf665e-a862-45fe-be69-74358637db3e*"
        }
    }
}

RESPONSE_WITH_ONE_LOG = ''

RESPONSE_WITH_NO_RESULT = """{
  "took" : 2913,
  "timed_out" : false,
  "_shards" : {
    "total" : 41,
    "successful" : 41,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 0,
      "relation" : "eq"
    },
    "max_score" : null,
    "hits" : [ ]
  }
}"""


@pytest.mark.parametrize(
    "response_text",
    [
        RESPONSE_WITH_ONE_LOG,
    ]
)
def test_response_get_log(response_text):
    '''Test Response.get_log()'''

    result = Response.get_log(response_text)

    assert isinstance(result, list), (
        f"Expected result as dict, got {type(result)}"
    )
    assert all([isinstance(itm, dict) for itm in result]), (
        "Expected result instances to be list"
    )


@pytest.mark.parametrize(
    "response_text",
    [
        RESPONSE_WITH_ONE_LOG,
        RESPONSE_WITH_NO_RESULT,
    ]
)
def test_response_get_log_and_message(response_text):
    '''Test Response.get_message()'''

    result = Response.get_log(response_text)
    result = Response.get_message(result)

    assert isinstance(result, list), (
        f"Expected result as dict, got {type(result)}"
    )
    assert all([isinstance(itm, str) for itm in result]), (
        "Expected result instances to be str"
    )


@pytest.mark.parametrize(
    "response_text",
    [
        RESPONSE_WITH_ONE_LOG,
        RESPONSE_WITH_NO_RESULT,
    ]
)
def test_response_plane_text_getter_and_setter(response_text):
    '''Test Response.plane_text getter and setter'''

    response = Response(response_text)

    assert isinstance(response.plane_text, str), (
        f"response.plane_text must be string. Got: {type(response.plane_text)}"
    )
    assert isinstance(response.log, dict), (
        f"response.log must be string. Got: {type(response.log)}"
    )

    assert isinstance(response.message, str), (
        f"response.message must be string. Got: {type(response.message)}"
    )
