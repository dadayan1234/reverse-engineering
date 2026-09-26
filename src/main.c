#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "research_markers.h"

static const char *TAG = "research_app";
static volatile size_t marker_use = 0;
static const char research_api_key[] = RESEARCH_API_KEY;
static const char research_static_secret[] = RESEARCH_STATIC_SECRET;

static void use_compiled_markers(void)
{
    const volatile char *markers[] = {research_api_key, research_static_secret};
    for (size_t index = 0; index < 2; ++index) {
        for (const volatile char *cursor = markers[index]; *cursor; ++cursor) {
            marker_use += (unsigned char)*cursor;
        }
    }
}

static void wifi_events(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    (void)data;
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
        ESP_LOGI(TAG, "Wi-Fi connection requested");
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "Wi-Fi disconnected; retrying");
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ESP_LOGI(TAG, "Wi-Fi connected");
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "ESP32-S3 thesis research application starting");
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS requires erase/reinitialization");
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    nvs_handle_t handle;
    if (nvs_open("research", NVS_READWRITE, &handle) == ESP_OK) {
        if (nvs_set_str(handle, "nvs_secret", RESEARCH_NVS_SECRET) == ESP_OK) {
            ESP_ERROR_CHECK(nvs_commit(handle));
            ESP_LOGI(TAG, "Synthetic NVS marker stored");
        }
        nvs_close(handle);
    }

    use_compiled_markers();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_events, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_events, NULL));
    wifi_config_t cfg = { 0 };
    memcpy(cfg.sta.ssid, RESEARCH_WIFI_SSID, sizeof(RESEARCH_WIFI_SSID));
    memcpy(cfg.sta.password, RESEARCH_WIFI_PASSWORD, sizeof(RESEARCH_WIFI_PASSWORD));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &cfg));
    ESP_ERROR_CHECK(esp_wifi_start());
    for (;;) {
        ESP_LOGI(TAG, "heartbeat: application healthy, marker checksum %u", (unsigned)marker_use);
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
