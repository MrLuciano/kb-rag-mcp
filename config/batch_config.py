"""
PHASE 8: Batch processing configuration and tuning.

Centralizes all batch-related configuration with auto-tuning
based on available resources.
"""

import os
import psutil


def get_optimal_batch_sizes() -> dict[str, int]:
    """
    Auto-tune batch sizes based on available RAM and CPU cores.
    
    Returns:
        Dict with optimal batch sizes for different operations
    """
    # Get system resources
    available_ram_gb = psutil.virtual_memory().available / (1024**3)
    cpu_count = psutil.cpu_count() or 2
    
    # Base values (for 8GB RAM, 4 cores)
    base_embed_batch = 32
    base_file_batch = 50
    base_qdrant_batch = 100
    base_pool_size = 20
    
    # Scale based on RAM (linear scaling)
    ram_factor = min(available_ram_gb / 8.0, 4.0)  # Cap at 4x
    
    # Scale based on CPU (sqrt scaling to avoid over-parallelization)
    cpu_factor = min((cpu_count / 4.0) ** 0.5, 2.0)  # Cap at 2x
    
    return {
        # Embedding batch size (texts per API call)
        "embed_batch_size": int(base_embed_batch * ram_factor),
        # File batch size (files to parse together)
        "file_batch_size": int(base_file_batch * cpu_factor),
        # Qdrant batch size (points per upsert)
        "qdrant_batch_size": int(base_qdrant_batch * ram_factor),
        # HTTP connection pool size
        "http_pool_size": int(base_pool_size * cpu_factor),
        # Max parallel Qdrant batches
        "qdrant_parallel_batches": min(int(2 * cpu_factor), 5),
        # Worker pool size
        "num_workers": min(cpu_count, 8),
    }


# Configuration with environment variable overrides and auto-tuning
_AUTO_CONFIG = get_optimal_batch_sizes()

# Embedding configuration
EMBED_BATCH_SIZE = int(
    os.getenv("EMBED_BATCH_SIZE", str(_AUTO_CONFIG["embed_batch_size"]))
)

# File processing configuration
FILE_BATCH_SIZE = int(
    os.getenv("FILE_BATCH_SIZE", str(_AUTO_CONFIG["file_batch_size"]))
)

# Qdrant configuration
QDRANT_BATCH_SIZE = int(
    os.getenv("QDRANT_BATCH_SIZE", str(_AUTO_CONFIG["qdrant_batch_size"]))
)
QDRANT_PARALLEL_BATCHES = int(
    os.getenv(
        "QDRANT_PARALLEL_BATCHES",
        str(_AUTO_CONFIG["qdrant_parallel_batches"]),
    )
)

# Connection pool configuration
HTTP_POOL_CONNECTIONS = int(
    os.getenv(
        "HTTP_POOL_CONNECTIONS", str(_AUTO_CONFIG["http_pool_size"])
    )
)
HTTP_POOL_MAXSIZE = int(
    os.getenv("HTTP_POOL_MAXSIZE", str(HTTP_POOL_CONNECTIONS * 2))
)

# Worker pool configuration
NUM_WORKERS = int(
    os.getenv("NUM_WORKERS", str(_AUTO_CONFIG["num_workers"]))
)


def get_config_summary() -> dict:
    """
    Get current batch configuration summary.
    
    Returns:
        Dict with all configuration values and system info
    """
    mem = psutil.virtual_memory()
    
    return {
        "system": {
            "cpu_count": psutil.cpu_count(),
            "ram_total_gb": mem.total / (1024**3),
            "ram_available_gb": mem.available / (1024**3),
            "ram_percent": mem.percent,
        },
        "batch_config": {
            "embed_batch_size": EMBED_BATCH_SIZE,
            "file_batch_size": FILE_BATCH_SIZE,
            "qdrant_batch_size": QDRANT_BATCH_SIZE,
            "qdrant_parallel_batches": QDRANT_PARALLEL_BATCHES,
            "http_pool_connections": HTTP_POOL_CONNECTIONS,
            "http_pool_maxsize": HTTP_POOL_MAXSIZE,
            "num_workers": NUM_WORKERS,
        },
        "auto_tuned": _AUTO_CONFIG,
    }


def print_config() -> None:
    """Print configuration summary in human-readable format."""
    config = get_config_summary()
    
    print("=" * 60)
    print("PHASE 8: Batch Processing Configuration")
    print("=" * 60)
    
    print("\nSystem Resources:")
    sys_info = config["system"]
    print(f"  CPU Cores:        {sys_info['cpu_count']}")
    print(f"  RAM Total:        {sys_info['ram_total_gb']:.1f} GB")
    print(f"  RAM Available:    {sys_info['ram_available_gb']:.1f} GB")
    print(f"  RAM Usage:        {sys_info['ram_percent']:.1f}%")
    
    print("\nBatch Configuration:")
    batch = config["batch_config"]
    print(f"  Embed Batch:      {batch['embed_batch_size']} texts/call")
    print(f"  File Batch:       {batch['file_batch_size']} files/batch")
    print(f"  Qdrant Batch:     {batch['qdrant_batch_size']} points/upsert")
    print(
        f"  Qdrant Parallel:  {batch['qdrant_parallel_batches']} batches"
    )
    print(f"  HTTP Pool:        {batch['http_pool_connections']} connections")
    print(f"  Worker Pool:      {batch['num_workers']} workers")
    
    print("\nAuto-Tuned Recommendations:")
    auto = config["auto_tuned"]
    for key, value in auto.items():
        env_var = key.upper()
        print(f"  {env_var}={value}")
    
    print("\nTo override, set environment variables:")
    print("  export EMBED_BATCH_SIZE=64")
    print("  export FILE_BATCH_SIZE=100")
    print("  export NUM_WORKERS=4")
    print("=" * 60)


if __name__ == "__main__":
    print_config()
