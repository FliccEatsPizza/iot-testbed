/*
 * Standby / Idle Firmware for IoT Testbed nRF52840 Dongle (PCA10059)
 * 
 * Purpose:
 *  - Disables the 802.15.4 radio transceiver so the node emits ZERO RF packets.
 *  - Turns off all LEDs (dark standby).
 *  - Maintains USB CDC-ACM active so the host can issue a 1200-baud touch
 *    reset into Open DFU Bootloader at any time for the next experiment.
 */

#include "contiki.h"
#include "net/netstack.h"
#include "dev/leds.h"
#include <stdio.h>

PROCESS(idle_node_process, "Idle Standby Node");
AUTOSTART_PROCESSES(&idle_node_process);

PROCESS_THREAD(idle_node_process, ev, data)
{
  PROCESS_BEGIN();

  /* 1. Explicitly turn off 802.15.4 radio transceiver */
  NETSTACK_RADIO.off();

  /* 2. Turn off all LEDs (dark standby) */
  leds_off(LEDS_ALL);

  /* 3. Output confirmation to USB CDC-ACM serial */
  printf("\n========================================\n");
  printf(" [IDLE] Device placed in STANDBY mode.\n");
  printf(" [IDLE] 802.15.4 Radio: OFF\n");
  printf(" [IDLE] USB CDC-ACM: ACTIVE (Ready for DFU)\n");
  printf("========================================\n\n");

  /* 4. Sleep indefinitely - yields to Contiki main loop for USB CDC ACM */
  while(1) {
    PROCESS_YIELD();
  }

  PROCESS_END();
}
