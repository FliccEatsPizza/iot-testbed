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
/* Simple URL dispatcher:
 *   GET /           -> sensor JSON (temp, hum, led)
 *   GET /led/on     -> turns ON physical LED and returns confirmation JSON
 *   GET /led/off    -> turns OFF physical LED and returns confirmation JSON
 *   GET /led/toggle -> toggles physical LED
 */
httpd_simple_script_t
httpd_simple_get_script(const char *name)
{
  if(name == NULL || strcmp(name, "") == 0 || strcmp(name, "index.html") == 0) {
    return generate_sensor_data;
  }
  if(strcmp(name, "led/on") == 0 || strcmp(name, "on") == 0) {
    g_led_state = 1;
    leds_on(LEDS_ALL);
    printf("⚡ [ACTUATION] LED ON command executed\n");
    return generate_actuation;
  }
  if(strcmp(name, "led/off") == 0 || strcmp(name, "off") == 0) {
    g_led_state = 0;
    leds_off(LEDS_ALL);
    printf("⚡ [ACTUATION] LED OFF command executed\n");
    return generate_actuation;
  }
  if(strcmp(name, "led/toggle") == 0 || strcmp(name, "toggle") == 0) {
    g_led_state = !g_led_state;
    if(g_led_state) {
      leds_on(LEDS_ALL);
    } else {
      leds_off(LEDS_ALL);
    }
    printf("⚡ [ACTUATION] LED TOGGLE command executed (state=%d)\n", g_led_state);
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

  /* Ensure LEDs start in known OFF state */
  leds_off(LEDS_ALL);
  g_led_state = 0;

  PROCESS_NAME(webserver_nogui_process);
  process_start(&webserver_nogui_process, NULL);

  LOG_INFO("Web Sense started with Actuation support\n");

  PROCESS_END();
}