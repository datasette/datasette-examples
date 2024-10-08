from datasette.app import Datasette
import pytest
import sqlite3


@pytest.fixture
def mocked_httpx(httpx_mock):
    mock_sql_content = """
    CREATE TABLE demo (
        id INTEGER PRIMARY KEY,
        name TEXT,
        value INTEGER
    );
    INSERT INTO demo (name, value) VALUES ('test', 42);
    """
    httpx_mock.add_response(
        url="https://www.example.com/demo.sql", text=mock_sql_content
    )
    return httpx_mock


def build_datasette(tmp_path_factory):
    db_directory = tmp_path_factory.mktemp("dbs")
    db_path = db_directory / "examples.db"
    db = sqlite3.connect(db_path)
    db.execute("vacuum")
    ds = Datasette(
        [db_path],
        metadata={
            "plugins": {
                "datasette-examples": {
                    "startup": {
                        "examples": [
                            {
                                "url": "https://www.example.com/demo.sql",
                                "if_not_table": "demo",
                            }
                        ]
                    }
                }
            }
        },
    )
    return ds


@pytest.mark.asyncio
async def test_datasette_examples_plugin(tmp_path_factory, mocked_httpx):
    ds = build_datasette(tmp_path_factory)
    await ds.invoke_startup()

    # Verify that the mock was called with the correct URL
    assert mocked_httpx.get_requests()[0].url == "https://www.example.com/demo.sql"

    # Table should exist
    response = await ds.client.get("/examples/demo.json")
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_datasette_examples_plugin_table_exists(tmp_path_factory, mocked_httpx):
    ds = build_datasette(tmp_path_factory)
    await ds.get_database().execute_write("CREATE TABLE demo (id INTEGER PRIMARY KEY)")
    await ds.invoke_startup()
    # Verify that no HTTP request was made
    assert mocked_httpx.get_requests() == []
