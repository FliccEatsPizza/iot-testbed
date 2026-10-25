#include "contiki.h"
#include "sys/etimer.h"
#include <stdio.h>

PROCESS(hello_world_periodic, "Hello world periodic");
AUTOSTART_PROCESSES(&hello_world_periodic);

PROCESS_THREAD(hello_world_periodic, ev, data)
{
  static struct etimer timer;
  static int counter = 1;
  PROCESS_BEGIN();

  printf("====================================\n");
  printf("Contiki-NG Hello World Lab Started!\n");
  printf("Target: nRF52840 Dongle\n");
  printf("====================================\n");

  /* Setup a periodic timer that expires every 5 seconds. */
  etimer_set(&timer, CLOCK_SECOND * 5);

  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&timer));
    printf("[Hello Lab] Count %d: Hello from Contiki-NG node!\n", counter++);
    etimer_reset(&timer);
  }

  PROCESS_END();
}
