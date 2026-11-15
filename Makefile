# Build on the cluster:   module load pp && run -c 4 -- make -j4
# Run tests:              run -c 4 -- make test
#
# Two builds of the same sources:
#   build/normal  -> bin/sssp, bin/test_sssp           (timing runs, no counters)
#   build/stats   -> bin/sssp_stats, bin/test_sssp_stats (-DSSSP_STATS: work/depth counters, phase log)
#
# Overridable: CXX, ARCH (default native; build on a compute node via `run`),
# OPT, SAN (e.g. make debug).

.RECIPEPREFIX := >

CXX      ?= g++
ARCH     ?= native
OPT      ?= -O3
SAN      ?=
BUILD    ?= build
BIN      ?= bin

CXXFLAGS := $(OPT) -march=$(ARCH) -std=c++20 -fopenmp -Wall -Wextra -Iinclude -MMD -MP $(SAN)
LDFLAGS  := -fopenmp $(SAN)

LIB_SRCS := src/graph.cpp src/edgelist.cpp src/generators.cpp src/dijkstra.cpp \
            src/delta_common.cpp src/delta_seq.cpp src/delta_omp.cpp

LIB_N := $(LIB_SRCS:%.cpp=$(BUILD)/normal/%.o)
LIB_S := $(LIB_SRCS:%.cpp=$(BUILD)/stats/%.o)

PROGS := $(BIN)/sssp $(BIN)/sssp_stats $(BIN)/convert $(BIN)/gen $(BIN)/profile \
         $(BIN)/test_sssp $(BIN)/test_sssp_stats

.PHONY: all test debug clean
.SECONDARY:

all: $(PROGS)

$(BUILD)/normal/%.o: %.cpp
> @mkdir -p $(@D)
> $(CXX) $(CXXFLAGS) -c $< -o $@

$(BUILD)/stats/%.o: %.cpp
> @mkdir -p $(@D)
> $(CXX) $(CXXFLAGS) -DSSSP_STATS -c $< -o $@

$(BIN)/sssp: $(BUILD)/normal/src/main_sssp.o $(LIB_N)
> @mkdir -p $(@D)
> $(CXX) $^ -o $@ $(LDFLAGS)

$(BIN)/sssp_stats: $(BUILD)/stats/src/main_sssp.o $(LIB_S)
> @mkdir -p $(@D)
> $(CXX) $^ -o $@ $(LDFLAGS)

$(BIN)/test_sssp: $(BUILD)/normal/tests/test_main.o $(LIB_N)
> @mkdir -p $(@D)
> $(CXX) $^ -o $@ $(LDFLAGS)

$(BIN)/test_sssp_stats: $(BUILD)/stats/tests/test_main.o $(LIB_S)
> @mkdir -p $(@D)
> $(CXX) $^ -o $@ $(LDFLAGS)

$(BIN)/%: $(BUILD)/normal/tools/%.o $(LIB_N)
> @mkdir -p $(@D)
> $(CXX) $^ -o $@ $(LDFLAGS)

test: $(BIN)/test_sssp $(BIN)/test_sssp_stats
> ./$(BIN)/test_sssp tests/testcase
> ./$(BIN)/test_sssp_stats tests/testcase

# AddressSanitizer + UBSan build in separate directories.
debug:
> $(MAKE) BUILD=build/debug BIN=bin/debug OPT="-O1 -g" SAN="-fsanitize=address,undefined -fno-omit-frame-pointer" all

clean:
> rm -rf build bin

-include $(shell find $(BUILD) -name '*.d' 2>/dev/null)
