/*
 * DHT11 Environmental Sensor Telemetry & Cloud MQTT Streaming Lab
 *
 * Contiki-NG firmware for nRF52840 Dongle.
 * Connects to DHT11 Temperature & Humidity Sensor on Port 1, Pin 15 (P1.15).
 * Uses Open-Drain GPIO mode with internal pull-up and cycle-accurate 1us timing.
 * Dispatches formatted MQTT publish directives to Gateway for cloud streaming.
 */

#include "contiki.h"
#include "dev/leds.h"
#include "nrf.h"
#include "nrf_gpio.h"
#include "nrf_delay.h"
#include <stdio.h>
#include <string.h>

#include "sys/log.h"
#define LOG_MODULE "DHT11-Cloud"
#define LOG_LEVEL LOG_LEVEL_INFO

#define SENSOR_PORT 1
#define SENSOR_PIN 15
#define PIN_NR NRF_GPIO_PIN_MAP(SENSOR_PORT, SENSOR_PIN)
#define SAMPLE_INTERVAL (4 * CLOCK_SECOND)

/*---------------------------------------------------------------------------*/
/* Robust Open-Drain cycle-accurate DHT11 bit-bang reader                    */
/*---------------------------------------------------------------------------*/
static int read_dht11(uint8_t *hum, uint8_t *temp, uint8_t raw[5])
{
  uint32_t timeout;
  int i;

  memset(raw, 0, 5);

  /* Configure pin as Open-Drain (S0D1) with internal pull-up and input connected.
   * Standard '0' drives line firmly to GND.
   * Disconnect '1' releases line to float up to 3.3V via internal pull-up.
   * This eliminates pin direction switching and prevents bus fighting. */
  nrf_gpio_cfg(
    PIN_NR,
    NRF_GPIO_PIN_DIR_OUTPUT,
    NRF_GPIO_PIN_INPUT_CONNECT,
    NRF_GPIO_PIN_PULLUP,
    NRF_GPIO_PIN_S0D1,
    NRF_GPIO_PIN_NOSENSE
  );

  /* Send start signal: pull line LOW for 20ms */
  nrf_gpio_pin_clear(PIN_NR);
  nrf_delay_ms(20);

  /* Disable interrupts before releasing line to prevent context-switch jitter */
  __disable_irq();

  /* Release line HIGH (disconnects output, internal pull-up pulls to 3.3V) */
  nrf_gpio_pin_set(PIN_NR);
  nrf_delay_us(30);

  /* Phase 1: Wait for DHT11 response - sensor pulls line LOW (within 20-40us) */
  timeout = 300;
  while(nrf_gpio_pin_read(PIN_NR) && --timeout) {
    nrf_delay_us(1);
  }
  if(!timeout) {
    __enable_irq();
    return -1; /* Timeout waiting for sensor LOW response */
  }

  /* Phase 2: Sensor holds line LOW for ~80us, then pulls HIGH */
  timeout = 300;
  while(!nrf_gpio_pin_read(PIN_NR) && --timeout) {
    nrf_delay_us(1);
  }
  if(!timeout) {
    __enable_irq();
    return -2; /* Timeout waiting for sensor HIGH response */
  }

  /* Phase 3: Sensor holds line HIGH for ~80us, then pulls LOW to start data bits */
  timeout = 300;
  while(nrf_gpio_pin_read(PIN_NR) && --timeout) {
    nrf_delay_us(1);
  }
  if(!timeout) {
    __enable_irq();
    return -3; /* Timeout waiting for data transmission start */
  }

  /* Phase 4: Sample 40 data bits */
  for(i = 0; i < 40; i++) {
    uint32_t high_duration = 0;

    /* Each bit begins with 50us LOW. Wait for line to go HIGH */
    timeout = 300;
    while(!nrf_gpio_pin_read(PIN_NR) && --timeout) {
      nrf_delay_us(1);
    }
    if(!timeout) {
      __enable_irq();
      return -4; /* Timeout waiting for bit pulse */
    }

    /* Measure duration of HIGH pulse (1us resolution) */
    while(nrf_gpio_pin_read(PIN_NR) && high_duration < 300) {
      nrf_delay_us(1);
      high_duration++;
    }

    /* DHT11 bit timing: 26-28us = '0', 70us = '1'. Midpoint threshold = 45us */
    uint8_t bit = (high_duration > 45) ? 1 : 0;
    raw[i / 8] = (raw[i / 8] << 1) | bit;
  }

  __enable_irq();

  /* Verify 8-bit checksum */
  uint8_t expected_chk = (raw[0] + raw[1] + raw[2] + raw[3]) & 0xFF;
  if(expected_chk != raw[4]) {
    return -5; /* Checksum mismatch */
  }

  *hum = raw[0];
  *temp = raw[2];
  return 0;
}

/*---------------------------------------------------------------------------*/
PROCESS(dht11_cloud_process, "DHT11 Cloud Telemetry Process");
AUTOSTART_PROCESSES(&dht11_cloud_process);
/*---------------------------------------------------------------------------*/
PROCESS_THREAD(dht11_cloud_process, ev, data)
{
  static struct etimer timer;
  static uint32_t sample_count = 0;
  uint8_t hum, temp, raw[5];
  int res;

  PROCESS_BEGIN();

  LOG_INFO("====================================================\n");
  LOG_INFO("🌐 DHT11 Environmental Telemetry & Cloud MQTT Lab\n");
  LOG_INFO("📍 GPIO Config: Port %d, Pin %d (P1.15) [OPEN-DRAIN PULL-UP]\n", SENSOR_PORT, SENSOR_PIN);
  LOG_INFO("📡 Cloud Topic: iot-testbed/dht11/telemetry\n");
  LOG_INFO("⏱️ Sampling Rate: every 4 seconds\n");
  LOG_INFO("====================================================\n");

  /* Initial setup: configure pin in open-drain mode with pull-up */
  nrf_gpio_cfg(
    PIN_NR,
    NRF_GPIO_PIN_DIR_OUTPUT,
    NRF_GPIO_PIN_INPUT_CONNECT,
    NRF_GPIO_PIN_PULLUP,
    NRF_GPIO_PIN_S0D1,
    NRF_GPIO_PIN_NOSENSE
  );
  nrf_gpio_pin_set(PIN_NR);

  /* Set initial sample timer */
  etimer_set(&timer, 2 * CLOCK_SECOND);

  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&timer));

    sample_count++;

    /* Flash LED on activity */
    leds_on(LEDS_ALL);

    res = read_dht11(&hum, &temp, raw);

    if(res == 0) {
      LOG_INFO("🌡️ [Sample #%lu] Temp: %u°C | 💧 Humidity: %u%%\n",
               (unsigned long)sample_count, temp, hum);

      /* Machine-parseable line forwarded by Gateway to HiveMQ Cloud */
      printf("MQTT:PUBLISH topic=\"iot-testbed/dht11/telemetry\" payload={\"sample\":%lu,\"temperature\":%u,\"humidity\":%u,\"unit_temp\":\"C\",\"unit_hum\":\"%%\",\"status\":\"OK\"}\n",
             (unsigned long)sample_count, temp, hum);
    } else if(res == -5) {
      uint8_t expected = (raw[0] + raw[1] + raw[2] + raw[3]) & 0xFF;
      LOG_WARN("⚠️ [Sample #%lu] Checksum mismatch! Raw: [%u, %u, %u, %u, chk=%u] (expected=%u)\n",
               (unsigned long)sample_count, raw[0], raw[1], raw[2], raw[3], raw[4], expected);
    } else if(res == -1) {
      LOG_WARN("⚠️ [Sample #%lu] Timeout (Phase 1): Sensor did not pull line LOW. Verify node with DHT11 is selected.\n",
               (unsigned long)sample_count);
    } else if(res == -2) {
      LOG_WARN("⚠️ [Sample #%lu] Timeout (Phase 2): Sensor did not release line HIGH.\n",
               (unsigned long)sample_count);
    } else if(res == -3) {
      LOG_WARN("⚠️ [Sample #%lu] Timeout (Phase 3): Sensor did not start data burst.\n",
               (unsigned long)sample_count);
    } else if(res == -4) {
      LOG_WARN("⚠️ [Sample #%lu] Timeout (Phase 4): Incomplete data burst.\n",
               (unsigned long)sample_count);
    } else {
      LOG_WARN("⚠️ [Sample #%lu] Reading error code: %d\n",
               (unsigned long)sample_count, res);
    }

    leds_off(LEDS_ALL);

    /* Schedule next periodic sample */
    etimer_reset(&timer);
  }

  PROCESS_END();
}
/*---------------------------------------------------------------------------*/
