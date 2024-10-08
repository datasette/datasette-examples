from datasette import hookimpl
import click
import httpx


@hookimpl
def startup(datasette):
    async def inner():
        config = datasette.plugin_config("datasette-examples") or {}
        startup_config = config.get("startup", {})
        print("startup_config", startup_config)
        for db_name, examples in startup_config.items():
            db = datasette.get_database(db_name)
            if not db:
                raise click.ClickException(f"Database {db_name} not found")
            for example in examples:
                url = example["url"]
                if_not_table = example["if_not_table"]
                if not await db.table_exists(if_not_table):
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(url)
                            response.raise_for_status()
                            sql_content = response.text

                        def execute_sql(conn):
                            conn.executescript(sql_content)

                        await db.execute_write_fn(execute_sql)
                        click.secho(
                            f"Executed SQL from {url} in database {db_name}",
                            fg="green",
                            err=True,
                        )
                    except Exception as e:
                        click.secho(
                            f"Error executing SQL from {url}: {str(e)}",
                            fg="red",
                            err=True,
                        )

    return inner
