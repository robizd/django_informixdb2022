from unittest.mock import Mock, call

import pyodbc
import pytest

from django_informixdb.base import DatabaseWrapper


def test_DatabaseWrapper_get_new_connection_calls_pyodbc_connect(mocker):
    mock_connect = mocker.patch("pyodbc.connect", autospec=True)
    db = DatabaseWrapper({
        "SERVER": "server1", "NAME": "db1", "USER": "user1", "PASSWORD": "password1"
    })
    db.get_new_connection(db.get_connection_params())
    assert mock_connect.called is True
    connection_string = mock_connect.call_args[0][0]
    parts = connection_string.split(";")
    assert "Server=server1" in parts
    assert "Database=db1" in parts
    assert "Uid=user1" in parts
    assert "Pwd=password1" in parts


def test_get_new_connection_doesnt_retry_by_default(mocker):
    mock_connect = mocker.patch(
        "pyodbc.connect",
        autospec=True,
        side_effect=pyodbc.Error(),
    )
    db = DatabaseWrapper({
        "SERVER": "server1", "NAME": "db1", "USER": "user1", "PASSWORD": "password1"
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 1


def test_get_new_connection_retries_up_to_MAX_ATTEMPTS(mocker):
    mock_sleep = mocker.patch("time.sleep", autospec=True)
    mock_connect = mocker.patch("pyodbc.connect", autospec=True, side_effect=pyodbc.Error())
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 3,
        },
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 3
    assert mock_sleep.call_count == 2


def test_get_new_connection_breaks_early_if_connection_succeeds(mocker):
    mock_sleep = mocker.patch("time.sleep", autospec=True)
    mock_connect = mocker.patch(
        "pyodbc.connect",
        autospec=True,
        side_effect=[pyodbc.Error(), Mock()],
    )
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 3,
        },
    })
    db.get_new_connection(db.get_connection_params())
    assert mock_connect.call_count == 2
    assert mock_sleep.call_count == 1


def test_sleeps_between_connection_attempts(mocker):
    mock_uniform = mocker.patch(
        "random.uniform",
        autospec=True,
        side_effect=[1000, 2000, 3000, 4000, 5000],
    )
    mock_sleep = mocker.patch("time.sleep", autospec=True)
    mocker.patch("pyodbc.connect", autospec=True, side_effect=pyodbc.Error())
    db = DatabaseWrapper({
        "SERVER": "server1",
        "NAME": "db1",
        "USER": "user1",
        "PASSWORD": "password1",
        "CONNECTION_RETRY": {
            "MAX_ATTEMPTS": 6,
            "WAIT_MIN": 15,
            "WAIT_MAX": 100,
            "WAIT_MULTIPLIER": 10,
            "WAIT_EXP_BASE": 2,
        },
    })
    with pytest.raises(pyodbc.Error):
        db.get_new_connection(db.get_connection_params())
    assert mock_uniform.call_args_list == [
        call(15, 15),
        call(15, 20),
        call(15, 40),
        call(15, 80),
        call(15, 100),
    ]
    assert mock_sleep.call_args_list == [call(1), call(2), call(3), call(4), call(5)]
