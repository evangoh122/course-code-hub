# Databricks notebook source
# MAGIC %md
# MAGIC # Initialize the Genie source table
# MAGIC
# MAGIC Create the schema and an empty Delta table if missing. Existing data is
# MAGIC preserved. Ingestion and Lakebase synchronization run in a separate job.

# COMMAND ----------

from loguru import logger
from pyspark.sql import SparkSession

from arxiv_curator.config import get_env, load_config

spark = SparkSession.builder.getOrCreate()
cfg = load_config("../../project_config.yml", env=get_env(spark))

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {cfg.catalog}.{cfg.schema}")
# Match DataProcessor.download_and_store_papers, including its ingest_ts column.
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {cfg.catalog}.{cfg.schema}.arxiv_papers (
        arxiv_id STRING NOT NULL,
        title STRING,
        authors ARRAY<STRING>,
        summary STRING,
        pdf_url STRING,
        published BIGINT,
        processed BIGINT,
        volume_path STRING,
        ingest_ts TIMESTAMP
    ) USING DELTA
""")
logger.info(f"Genie source table ready: {cfg.catalog}.{cfg.schema}.arxiv_papers")
