#include "contiki.h"
#include "rpl.h"
#include "httpd-simple.h"
#include "dev/leds.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Log configuration */
#include "sys/log.h"
#define LOG_MODULE "Web Sense DB"
#define LOG_LEVEL LOG_LEVEL_INFO

static int g_led_state = 0;

/* Helper to turn all physical LEDs ON on the nRF52840 Dongle */
static void set_physical_leds(int state)
{
  g_led_state = state;
  if(state) {
    leds_on(LEDS_ALL);
    leds_single_on(0); /* Green LED (P0.06) */
    leds_single_on(1); /* Red RGB   (P0.08) */
    leds_single_on(2); /* Green RGB (P1.09) */
    leds_single_on(3); /* Blue RGB  (P0.12) */
    printf("💡 [HARDWARE] All physical LEDs turned ON!\n");
  } else {
    leds_off(LEDS_ALL);
    leds_single_off(0);
    leds_single_off(1);
    leds_single_off(2);
    leds_single_off(3);
    printf("🌑 [HARDWARE] All physical LEDs turned OFF!\n");
  }
}

/*---------------------------------------------------------------------------*/
/* Handler for LED actuation responses */
static
PT_THREAD(generate_actuation(struct httpd_state *s))
{
  char buff[64];
  PSOCK_BEGIN(&s->sout);

  snprintf(buff, sizeof(buff), "{\"status\":\"ok\",\"actuation\":\"led\",\"state\":%d}", g_led_state);
  SEND_STRING(&s->sout, buff);

  PSOCK_END(&s->sout);
}

/*---------------------------------------------------------------------------*/
/* Handler for periodic sensor data readings */
static
PT_THREAD(generate_sensor_data(struct httpd_state *s))
{
  char buff[64];
  PSOCK_BEGIN(&s->sout);

  int temperature = 15 + rand() % 25;
  int humidity = 80 + rand() % 10;

  snprintf(buff, sizeof(buff), "{\"temp\":%u,\"hum\":%u,\"led\":%d}", temperature, humidity, g_led_state);
  printf("📤 Sent sensor reading: temp=%d, hum=%d, led=%d\n", temperature, humidity, g_led_state);

  SEND_STRING(&s->sout, buff);

  PSOCK_END(&s->sout);
}

/*---------------------------------------------------------------------------*/
PROCESS(webserver_nogui_process, "Web Sense-db server");
PROCESS_THREAD(webserver_nogui_process, ev, data)
{
  PROCESS_BEGIN();

  httpd_init();

  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(ev == tcpip_event);
    httpd_appcall(data);
  }

  PROCESS_END();
}

/*---------------------------------------------------------------------------*/
/* URL dispatcher:
 *   Contains "on"     -> turns ON physical LEDs
 *   Contains "off"    -> turns OFF physical LEDs
 *   Contains "toggle" -> toggles physical LEDs
 *   Otherwise         -> returns sensor reading JSON
 */
httpd_simple_script_t
httpd_simple_get_script(const char *name)
{
  if(name == NULL) {
    return generate_sensor_data;
  }

  printf("🌐 [HTTP] Incoming request path: \"%s\"\n", name);

  if(strstr(name, "toggle") != NULL) {
    set_physical_leds(!g_led_state);
    return generate_actuation;
  }

  if(strstr(name, "off") != NULL) {
    set_physical_leds(0);
    return generate_actuation;
  }

  if(strstr(name, "on") != NULL) {
    set_physical_leds(1);
    return generate_actuation;
  }

  return generate_sensor_data;
}

/*---------------------------------------------------------------------------*/
/* Declare and auto-start this file's process */
PROCESS(web_sense_db, "Web Sense-db");
AUTOSTART_PROCESSES(&web_sense_db);

/*---------------------------------------------------------------------------*/
PROCESS_THREAD(web_sense_db, ev, data)
{
  PROCESS_BEGIN();

  /* Blink once on boot to prove LED hardware control works */
  set_physical_leds(1);
  clock_delay_usec(50000);
  set_physical_leds(0);

  PROCESS_NAME(webserver_nogui_process);
  process_start(&webserver_nogui_process, NULL);

  LOG_INFO("Web Sense started with Actuation support\n");

  PROCESS_END();
}