CONTIKI_PROJECT = websense-cloud
all: $(CONTIKI_PROJECT)

CONTIKI = ../..

PROJECT_SOURCEFILES += httpd-simple.c

# Platforms missing gpio-hal.h
PLATFORMS_EXCLUDE += sky z1

# Platforms missing US_TO_RTIMERTICKS and RTIMERTICKS_TO_US
PLATFORMS_EXCLUDE += native 

include $(CONTIKI)/Makefile.include
