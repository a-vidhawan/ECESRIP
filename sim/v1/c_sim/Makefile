# =============================================================================
# Makefile — Hopfield network C simulation
# =============================================================================
# Targets
#   make            build release binary (./hopfield_sim)
#   make debug      build with AddressSanitizer + debug symbols
#   make clean      remove build artefacts
#   make test       run quick smoke test
# =============================================================================

CC      := gcc
CFLAGS  := -std=c11 -Wall -Wextra -Wpedantic -O2
LDFLAGS := -lm

# Source files (hopfield_train.c contains the internal helpers too)
SRCS    := hopfield_train.c hopfield_sim.c
HDRS    := hopfield.h
TARGET  := hopfield_sim

# -----------------------------------------------------------------------------
# Default: release build
# -----------------------------------------------------------------------------
.PHONY: all
all: $(TARGET)

$(TARGET): $(SRCS) $(HDRS)
	$(CC) $(CFLAGS) $(SRCS) -o $@ $(LDFLAGS)
	@echo "Built: $@"

# -----------------------------------------------------------------------------
# Debug build (AddressSanitizer, full debug info)
# -----------------------------------------------------------------------------
.PHONY: debug
debug: CFLAGS += -g3 -fsanitize=address,undefined -fno-omit-frame-pointer -O0
debug: LDFLAGS += -fsanitize=address,undefined
debug: $(TARGET)

# -----------------------------------------------------------------------------
# Smoke test
# -----------------------------------------------------------------------------
.PHONY: test
test: $(TARGET)
	@echo "--- Test: N=8, P=3, Hebbian ---"
	./$(TARGET) --N 8 --P 3 --rule hebbian --seed 42
	@echo ""
	@echo "--- Test: N=8, P=3, Storkey ---"
	./$(TARGET) --N 8 --P 3 --rule storkey --seed 42
	@echo ""
	@echo "--- Test: N=16, P=5, Hebbian ---"
	./$(TARGET) --N 16 --P 5 --rule hebbian --seed 7

# -----------------------------------------------------------------------------
# Clean
# -----------------------------------------------------------------------------
.PHONY: clean
clean:
	rm -f $(TARGET) *.o
