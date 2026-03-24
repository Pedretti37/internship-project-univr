from unittest.mock import patch, MagicMock
from app.models import Skill
from app.esco import escoAPI
import requests

# Decorator needed for reaching "requests.get" in main code 
@patch("app.esco.escoAPI.requests.get")
def test_get_esco_occupations_list_success(mock_get):
    
    # Fake HTTP response, for testing
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "_embedded": {
            "results": [
                {"uri": "http://esco/1", "title": "Software Developer"},
                {"uri": "http://esco/2", "title": "Data Scientist"}
            ]
        }
    }

    # "requests.get" will return our response
    mock_get.return_value = mock_response

    # Calling our function
    result = escoAPI.get_esco_occupations_list("Developer", "en")

    # Checking results
    assert len(result) == 2
    assert result[0]["title"] == "Software Developer"
    assert result[0]["uri"] == "http://esco/1"
    
    # Checking if requests.get is getting called at least once
    mock_get.assert_called_once()


@patch("app.esco.escoAPI.requests.get")
def test_get_esco_occupations_list_connection_error(mock_get):
    
    # "requests.get" will launch an exception, fake for testing
    mock_get.side_effect = Exception("Not connected to network")

    result = escoAPI.get_esco_occupations_list("Developer", "en")

    # Checking if result is empty
    assert result == []


@patch("app.esco.escoAPI.requests.get")
def test_get_esco_skills_list(mock_get):
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "_embedded": {
            "results": [
                {"uri": "http://skill/1", "title": "Python Programming"}
            ]
        }
    }

    # "requests.get" will return our response
    mock_get.return_value = mock_response

    result = escoAPI.get_esco_skills_list("Python", "en")

    # Checking results
    assert len(result) == 1
    assert isinstance(result[0], Skill)
    assert result[0].name == "Python Programming"
    assert result[0].level == 0

@patch("app.esco.escoAPI.requests.get")
def test_get_esco_skill_uri_by_name_success(mock_get):

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "_embedded": {
            "results": [
                {"uri": "http://esco/skill/python_123", "title": "Python programming"}
            ]
        }
    }
    mock_get.return_value = mock_response

    result = escoAPI.get_esco_skill_uri_by_name("Python")

    # Checking results
    assert result == "http://esco/skill/python_123"
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["text"] == "Python"
    assert kwargs["params"]["limit"] == 1  


@patch("app.esco.escoAPI.requests.get")
def test_get_esco_skill_uri_by_name_not_found(mock_get):

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "_embedded": {
            "results": []
        }
    }
    mock_get.return_value = mock_response

    result = escoAPI.get_esco_skill_uri_by_name("SkillInventata")

    # Check
    assert result is None


# --- TEST 3: Errore di connessione o HTTP Error ---
@patch("app.esco.escoAPI.requests.get")
def test_get_esco_skill_uri_by_name_error(mock_get):

    mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")

    result = escoAPI.get_esco_skill_uri_by_name("Python")

    assert result is None