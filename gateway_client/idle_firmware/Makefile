CONTIKI_PROJECT = idle-node
all: $(CONTIKI_PROJECT)

# Keep routing and duty cycling disabled to minimize footprint
MAKE_NET = MAKE_NET_NULLNET
MAKE_ROUTING = MAKE_ROUTING_NULLROUTING

CONTIKI ?= $(HOME)/Desktop/contiki-ng
include $(CONTIKI)/Makefile.include
