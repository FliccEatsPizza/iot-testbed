#include "contiki.h"
#include "net/netstack.h"
#include "net/nullnet/nullnet.h"
#include <string.h>
#include <stdio.h>

#include "sys/log.h"
#define LOG_MODULE "NullNet"
#define LOG_LEVEL LOG_LEVEL_INFO

#define SEND_INTERVAL (5 * CLOCK_SECOND)

PROCESS(nullnet_broadcast_process, "NullNet Broadcast Lab");
AUTOSTART_PROCESSES(&nullnet_broadcast_process);

void input_callback(const void *data, uint16_t len,
  const linkaddr_t *src, const linkaddr_t *dest)
{
  if(len == sizeof(unsigned)) {
    unsigned received_count;
    memcpy(&received_count, data, sizeof(received_count));
    LOG_INFO("📡 Received packet #%u from node: ", received_count);
    LOG_INFO_LLADDR(src);
    LOG_INFO_("\n");
  }
}

PROCESS_THREAD(nullnet_broadcast_process, ev, data)
{
  static struct etimer periodic_timer;
  static unsigned count = 0;

  PROCESS_BEGIN();

  LOG_INFO("====================================\n");
  LOG_INFO("NullNet Raw 802.15.4 Broadcast Lab\n");
  LOG_INFO("No IPv6/Routing Stack Overhead\n");
  LOG_INFO("====================================\n");

  /* Initialize NullNet */
  nullnet_buf = (uint8_t *)&count;
  nullnet_len = sizeof(count);
  nullnet_set_input_callback(input_callback);

  etimer_set(&periodic_timer, SEND_INTERVAL);
  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&periodic_timer));
    LOG_INFO("📢 Broadcasting packet #%u to all 802.15.4 neighbors...\n", count);

    memcpy(nullnet_buf, &count, sizeof(count));
    nullnet_len = sizeof(count);

    /* Direct MAC transmission without IP routing */
    NETSTACK_NETWORK.output(NULL);
    count++;
    etimer_reset(&periodic_timer);
  }

  PROCESS_END();
}
