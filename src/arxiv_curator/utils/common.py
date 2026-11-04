from databricks.sdk.runtime import dbutils
from delta.tables import DeltaTable
from pyspark.sql import SparkSession


def get_widget(name: str, default: str | None = None) -> str | None:
    """Get a Databricks widget value with a fallback default.

    :param name: Widget name.
    :param default: Default value if widget is not set.
    :return: Widget value or default.
    """

    try:
        return dbutils.widgets.get(name)
    except KeyError:
        return default


def get_delta_table_version(spark: SparkSession, full_table_name: str) -> str:
    """
    Get the latest version of a Delta table.

    :param spark: Spark session.
    :param full_table_name: Name of the delta table as {catalog}.{schema}.{name}.
    :return: Latest version of the Delta table.
    """
    delta_table = DeltaTable.forName(spark, full_table_name)
    return str(delta_table.history().select("version").first()[0])
