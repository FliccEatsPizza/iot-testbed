/*
 * DHT11 Environmental Sensor Telemetry & Cloud MQTT Streaming Lab
 *
 * Contiki-NG firmware for nRF52840 Dongle.
 * Connects to DHT11 Temperature & Humidity Sensor on Port 1, Pin 15 (P1.15).
 * Periodically samples sensor data and outputs formatted logs with MQTT directives.
 */

#include "contiki.h"
#include "dht11-sensor.h"
#include "dev/leds.h"
#include <stdio.h>

#include "sys/log.h"
#define LOG_MODULE "DHT11-Cloud"
#define LOG_LEVEL LOG_LEVEL_INFO

#define SENSOR_PORT 1
#define SENSOR_PIN 15
#define SAMPLE_INTERVAL (4 * CLOCK_SECOND)

/*---------------------------------------------------------------------------*/
PROCESS(dht11_cloud_process, "DHT11 Cloud Telemetry Process");
AUTOSTART_PROCESSES(&dht11_cloud_process);
/*---------------------------------------------------------------------------*/
PROCESS_THREAD(dht11_cloud_process, ev, data)
{
  static struct etimer timer;
  static uint32_t sample_count = 0;
  int temp, hum, stat;

  PROCESS_BEGIN();

  LOG_INFO("====================================================\n");
  LOG_INFO("🌐 DHT11 Environmental Telemetry & Cloud MQTT Lab\n");
  LOG_INFO("📍 GPIO Config: Port %d, Pin %d (P1.15)\n", SENSOR_PORT, SENSOR_PIN);
  LOG_INFO("📡 Cloud Topic: iot-testbed/dht11/telemetry\n");
  LOG_INFO("⏱️ Sampling Rate: every 4 seconds\n");
  LOG_INFO("====================================================\n");

  /* Configure DHT11 hardware pin */
  dht11_sensor.configure(DHT11_CONFIGURE_GPIO_PORT, SENSOR_PORT);
  dht11_sensor.configure(DHT11_CONFIGURE_GPIO_PIN, SENSOR_PIN);

  /* Set initial sample timer */
  etimer_set(&timer, 2 * CLOCK_SECOND);

  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&timer));

    /* Flash LED to indicate measurement activity */
    leds_on(LEDS_ALL);

    /* Trigger sensor conversion */
    dht11_sensor.configure(SENSORS_ACTIVE, 1);
    stat = dht11_sensor.status(0);

    sample_count++;

    if(stat == DHT11_STATUS_OKAY) {
      temp = dht11_sensor.value(DHT11_VALUE_TEMPERATURE_INTEGER);
      hum = dht11_sensor.value(DHT11_VALUE_HUMIDITY_INTEGER);

      LOG_INFO("🌡️ [Sample #%lu] Temp: %d°C | 💧 Humidity: %d%%\n",
               (unsigned long)sample_count, temp, hum);

      /* Machine-parseable line forwarded by Gateway to HiveMQ Cloud */
      printf("MQTT:PUBLISH topic=\"iot-testbed/dht11/telemetry\" payload={\"sample\":%lu,\"temperature\":%d,\"humidity\":%d,\"unit_temp\":\"C\",\"unit_hum\":\"%%\",\"status\":\"OK\"}\n",
             (unsigned long)sample_count, temp, hum);
    } else if(stat == DHT11_STATUS_CHECKSUM_FAILED) {
      LOG_WARN("⚠️ [Sample #%lu] Checksum mismatch from DHT11 sensor (retrying)...\n",
               (unsigned long)sample_count);
    } else if(stat == DHT11_STATUS_TIMEOUT) {
      LOG_WARN("⚠️ [Sample #%lu] Timeout reading DHT11 on P1.15. Check sensor connection.\n",
               (unsigned long)sample_count);
    } else {
      LOG_WARN("⚠️ [Sample #%lu] Unknown DHT11 status: %d\n",
               (unsigned long)sample_count, stat);
    }

    leds_off(LEDS_ALL);

    /* Schedule next periodic sample */
    etimer_reset(&timer);
  }

  PROCESS_END();
}
/*---------------------------------------------------------------------------*/
