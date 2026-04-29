CXX      ?= g++
CXXFLAGS  = -O2 -std=c++17 -Wall -Wextra -pedantic -Iinclude
LDFLAGS   = -lpthread

SRC = src/main.cpp \
      src/instance.cpp \
      src/matching.cpp \
      src/brute.cpp \
      src/smart.cpp

OBJ = $(SRC:.cpp=.o)

.PHONY: all test clean

all: 3dm

3dm: $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $(OBJ) $(LDFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

test: 3dm
	@bash tests/run_tests.sh

clean:
	rm -f $(OBJ) 3dm
