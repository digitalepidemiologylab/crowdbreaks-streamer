from stream.config import (Conf, StorageMode, ImageStorageMode, FilterConf,
                           ConfigManager)

config = [
        {
            "keywords": ["simon and garfunkel"],
            "lang": ["en"],
            "locales": ["en"],
            "slug": "simongarfunkel",
            "storage_mode": "TEST_MODE",
            "image_storage_mode": "INACTIVE",
            "model_endpoints": None
        },
        {
            "keywords": ["flabbergasted"],
            "lang": ["en"],
            "locales": ["en"],
            "slug": "flabbergasted",
            "storage_mode": "TEST_MODE",
            "image_storage_mode": "INACTIVE",
            "model_endpoints": None
        },
        {
            "keywords": ["flabbergasted", "astonished"],
            "lang": ["en"],
            "locales": ["en"],
            "slug": "flabberstonished",
            "storage_mode": "TEST_MODE",
            "image_storage_mode": "INACTIVE",
            "model_endpoints": None
        },
    ]


def test_init():
    config_manager = ConfigManager(config)

    assert config_manager.config == [
        Conf(**{
            "keywords": ["simon and garfunkel"],
            "lang": ["en"],
            "locales": ["en"],
            "slug": "simongarfunkel",
            "storage_mode": StorageMode.TEST_MODE,
            "image_storage_mode": ImageStorageMode.INACTIVE,
            "model_endpoints": None
        }),
        Conf(**{
            "keywords": ["flabbergasted"],
            "lang": ["en"],
            "locales": ["en"],
            "slug": "flabbergasted",
            "storage_mode": StorageMode.TEST_MODE,
            "image_storage_mode": ImageStorageMode.INACTIVE,
            "model_endpoints": None
        }),
        Conf(**{
            "keywords": ["flabbergasted", "astonished"],
            "lang": ["en"],
            "locales": ["en"],
            "slug": "flabberstonished",
            "storage_mode": StorageMode.TEST_MODE,
            "image_storage_mode": ImageStorageMode.INACTIVE,
            "model_endpoints": None
        })
    ], 'Incorrect load.'

    assert config_manager.filter_config == FilterConf(**{
        "keywords": set(
            ["simon and garfunkel", "flabbergasted", "astonished"]
        ),
        "lang": set(["en"])
    })
