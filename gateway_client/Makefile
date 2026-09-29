# Universal Contiki-NG Makefile for compiling projects in different directories
# Place this Makefile in your base directory

# Default values
TARGET ?= nrf52840
BOARD ?= dongle
PORT ?= /dev/ttyACM0
SRC_DIR ?= .

# Find the base directory where this Makefile is located
BASE_DIR := $(shell pwd)

# Path to Contiki-NG (update this to your actual path)
CONTIKI ?= $(HOME)/Desktop/contiki-ng

# Check if source directory exists
ifneq ($(shell test -d $(SRC_DIR) && echo yes),yes)
$(error Source directory $(SRC_DIR) does not exist)
endif

# Count C files in the source directory
C_FILES_COUNT := $(shell find $(SRC_DIR) -maxdepth 1 -name "*.c" | wc -l)
ifeq ($(C_FILES_COUNT),0)
$(error No C files found in $(SRC_DIR))
endif

# Main project logic
build:
	@echo "Building project in $(SRC_DIR)"
	@if [ -f "$(SRC_DIR)/Makefile" ]; then \
		echo "Found existing Makefile in $(SRC_DIR), using it..."; \
		VALID_TARGETS=""; \
		for proj in $$(grep -E "^CONTIKI_PROJECT[ \t]*=" "$(SRC_DIR)/Makefile" | cut -d'=' -f2); do \
			if [ -f "$(SRC_DIR)/$$proj.c" ]; then \
				VALID_TARGETS="$$VALID_TARGETS $$proj"; \
			fi; \
		done; \
		if [ -n "$$VALID_TARGETS" ]; then \
			echo "Building target(s) with source files:$$VALID_TARGETS"; \
			cd $(SRC_DIR) && make TARGET=$(TARGET) BOARD=$(BOARD) CONTIKI=$(CONTIKI) $$VALID_TARGETS; \
		else \
			cd $(SRC_DIR) && make TARGET=$(TARGET) BOARD=$(BOARD) CONTIKI=$(CONTIKI); \
		fi; \
	else \
		mkdir -p $(SRC_DIR)/build; \
		echo "CONTIKI_PROJECT = $$(basename $$(find $(SRC_DIR) -maxdepth 1 -name "*.c" | head -1 | sed 's/\.c$$//g'))" > $(SRC_DIR)/build/Makefile; \
		echo "all: \$$(CONTIKI_PROJECT)" >> $(SRC_DIR)/build/Makefile; \
		if grep -q "root_start" $(SRC_DIR)/*.c 2>/dev/null || echo "$(SRC_DIR)" | grep -qi "border"; then \
			echo "MODULES += os/services/rpl-border-router" >> $(SRC_DIR)/build/Makefile; \
			echo "Added RPL Border Router module to build"; \
		fi; \
		echo "CONTIKI = $(CONTIKI)" >> $(SRC_DIR)/build/Makefile; \
		echo "include \$$(CONTIKI)/Makefile.include" >> $(SRC_DIR)/build/Makefile; \
		cp $(SRC_DIR)/*.c $(SRC_DIR)/build/; \
		cp $(SRC_DIR)/*.h $(SRC_DIR)/build/ 2>/dev/null || true; \
		cd $(SRC_DIR)/build && make TARGET=$(TARGET) BOARD=$(BOARD); \
		cp $(SRC_DIR)/build/*.$(TARGET) $(SRC_DIR)/ 2>/dev/null || true; \
		echo "Build complete. Output files copied to $(SRC_DIR)"; \
	fi

flash:
	@echo "Flashing project in $(SRC_DIR)"
	@$(MAKE) -f $(BASE_DIR)/Makefile build SRC_DIR=$(SRC_DIR) TARGET=$(TARGET) BOARD=$(BOARD)
	@if [ -f "$(SRC_DIR)/Makefile" ]; then \
		PROJECT_NAME=""; \
		for proj in $$(grep -E "^CONTIKI_PROJECT[ \t]*=" "$(SRC_DIR)/Makefile" | cut -d'=' -f2); do \
			if [ -f "$(SRC_DIR)/$$proj.c" ]; then \
				PROJECT_NAME="$$proj"; \
				break; \
			fi; \
		done; \
		if [ -z "$$PROJECT_NAME" ]; then \
			PROJECT_NAME=$$(basename $$(find $(SRC_DIR) -maxdepth 1 -name "*.c" | head -1 | sed 's/\.c$$//g')); \
		fi; \
		echo "Flashing target: $$PROJECT_NAME to $(PORT)"; \
		cd $(SRC_DIR) && make TARGET=$(TARGET) BOARD=$(BOARD) CONTIKI=$(CONTIKI) $$PROJECT_NAME.dfu-upload PORT=$(PORT); \
	else \
		PROJECT_NAME=$$(basename $$(find $(SRC_DIR) -maxdepth 1 -name "*.c" | head -1 | sed 's/\.c$$//g')); \
		cd $(SRC_DIR)/build && make TARGET=$(TARGET) BOARD=$(BOARD) $$PROJECT_NAME.dfu-upload PORT=$(PORT); \
	fi

clean:
	@echo "Cleaning project in $(SRC_DIR)"
	@if [ -f "$(SRC_DIR)/Makefile" ]; then \
		cd $(SRC_DIR) && make TARGET=$(TARGET) BOARD=$(BOARD) CONTIKI=$(CONTIKI) clean; \
	else \
		rm -rf $(SRC_DIR)/build; \
		rm -f $(SRC_DIR)/*.$(TARGET) $(SRC_DIR)/*.hex $(SRC_DIR)/*.elf $(SRC_DIR)/*.bin $(SRC_DIR)/*.dfu; \
	fi

# Default target
.PHONY: build flash clean
all: build
