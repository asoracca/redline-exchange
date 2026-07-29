#include "redline/order_book.hpp"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Event {
  std::string event_type;
  std::string order_id;
  std::optional<redline::Side> side;
  std::optional<std::int64_t> quantity;
  std::optional<std::int64_t> price_ticks;
};

struct ReplayOutput {
  redline::LimitOrderBook book{"REPLAY"};
  std::vector<redline::Trade> trades;
  std::vector<std::int64_t> latencies_ns;
  double elapsed_seconds{0.0};
};

std::string trim(std::string value) {
  const auto first = value.find_first_not_of(" \t\r\n");
  if (first == std::string::npos) {
    return {};
  }
  const auto last = value.find_last_not_of(" \t\r\n");
  return value.substr(first, last - first + 1);
}

std::string uppercase(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(),
                 [](unsigned char character) {
                   return static_cast<char>(std::toupper(character));
                 });
  return value;
}

std::vector<std::string> split_csv(const std::string& line) {
  std::vector<std::string> fields;
  std::stringstream stream(line);
  std::string field;
  while (std::getline(stream, field, ',')) {
    fields.push_back(trim(field));
  }
  if (!line.empty() && line.back() == ',') {
    fields.emplace_back();
  }
  fields.resize(5);
  return fields;
}

std::vector<Event> read_events(const std::string& path) {
  std::ifstream input(path);
  if (!input) {
    throw std::runtime_error("cannot open event file: " + path);
  }
  std::string line;
  if (!std::getline(input, line) ||
      trim(line) != "event_type,order_id,side,quantity,price_ticks") {
    throw std::runtime_error(
        "CSV header must be: event_type,order_id,side,quantity,price_ticks");
  }

  std::vector<Event> events;
  std::size_t line_number = 1;
  while (std::getline(input, line)) {
    ++line_number;
    if (trim(line).empty()) {
      continue;
    }
    try {
      const auto fields = split_csv(line);
      Event event{uppercase(fields[0]), fields[1], std::nullopt, std::nullopt,
                  std::nullopt};
      if (event.order_id.empty()) {
        throw std::invalid_argument("order_id cannot be empty");
      }
      if (!fields[2].empty()) {
        event.side = redline::parse_side(fields[2]);
      }
      if (!fields[3].empty()) {
        event.quantity = std::stoll(fields[3]);
      }
      if (!fields[4].empty()) {
        event.price_ticks = std::stoll(fields[4]);
      }
      events.push_back(std::move(event));
    } catch (const std::exception& error) {
      throw std::runtime_error("invalid event on CSV line " +
                               std::to_string(line_number) + ": " + error.what());
    }
  }
  return events;
}

template <typename T>
T require(const std::optional<T>& value, const std::string& field) {
  if (!value.has_value()) {
    throw std::invalid_argument("missing required field: " + field);
  }
  return value.value();
}

void apply_event(redline::LimitOrderBook& book, const Event& event,
                 std::vector<redline::Trade>& trades) {
  std::vector<redline::Trade> produced;
  if (event.event_type == "LIMIT") {
    produced = book.submit_limit(event.order_id, require(event.side, "side"),
                                 require(event.quantity, "quantity"),
                                 require(event.price_ticks, "price_ticks"));
  } else if (event.event_type == "MARKET") {
    produced = book.submit_market(event.order_id, require(event.side, "side"),
                                  require(event.quantity, "quantity"));
  } else if (event.event_type == "CANCEL") {
    book.cancel(event.order_id);
  } else if (event.event_type == "REPLACE") {
    produced = book.replace(event.order_id, require(event.quantity, "quantity"),
                            event.price_ticks);
  } else {
    throw std::invalid_argument("unknown event_type: " + event.event_type);
  }
  trades.insert(trades.end(), produced.begin(), produced.end());
}

ReplayOutput replay(const std::vector<Event>& events, bool measure) {
  ReplayOutput result;
  result.latencies_ns.reserve(events.size());
  const auto replay_started = std::chrono::steady_clock::now();
  for (std::size_t index = 0; index < events.size(); ++index) {
    try {
      const auto started = std::chrono::steady_clock::now();
      apply_event(result.book, events[index], result.trades);
      const auto stopped = std::chrono::steady_clock::now();
      if (measure) {
        result.latencies_ns.push_back(
            std::chrono::duration_cast<std::chrono::nanoseconds>(stopped - started)
                .count());
      }
    } catch (const std::exception& error) {
      throw std::runtime_error("failed to apply event " +
                               std::to_string(index + 1) + " (" +
                               events[index].event_type + " " +
                               events[index].order_id + "): " + error.what());
    }
  }
  const auto replay_stopped = std::chrono::steady_clock::now();
  result.elapsed_seconds =
      std::chrono::duration<double>(replay_stopped - replay_started).count();
  result.book.assert_invariants();
  return result;
}

void write_trades(const std::string& path,
                  const std::vector<redline::Trade>& trades) {
  std::ofstream output(path);
  output << "sequence,symbol,price_ticks,quantity,maker_order_id,taker_order_id,"
            "taker_side\n";
  for (const auto& trade : trades) {
    output << trade.sequence << ',' << trade.symbol << ',' << trade.price_ticks << ','
           << trade.quantity << ',' << trade.maker_order_id << ','
           << trade.taker_order_id << ',' << redline::to_string(trade.taker_side)
           << '\n';
  }
}

void write_orders(const std::string& path,
                  const std::vector<redline::Order>& orders) {
  std::ofstream output(path);
  output << "order_id,side,quantity,remaining,sequence,price_ticks\n";
  for (const auto& order : orders) {
    output << order.order_id << ',' << redline::to_string(order.side) << ','
           << order.quantity << ',' << order.remaining << ',' << order.sequence << ','
           << order.price_ticks.value() << '\n';
  }
}

double percentile(std::vector<std::int64_t> values, double probability) {
  std::ranges::sort(values);
  const auto index = static_cast<std::size_t>(
      std::llround(static_cast<double>(values.size() - 1) * probability));
  return static_cast<double>(values.at(index)) / 1'000.0;
}

std::string argument_value(int argc, char** argv, const std::string& name) {
  for (int index = 3; index + 1 < argc; ++index) {
    if (name == argv[index]) {
      return argv[index + 1];
    }
  }
  throw std::invalid_argument("missing argument: " + name);
}

void usage() {
  std::cerr << "usage:\n"
            << "  redline_cpp replay EVENTS --trades TRADES --orders ORDERS\n"
            << "  redline_cpp benchmark EVENTS --csv RESULTS\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 3) {
      usage();
      return 2;
    }
    const std::string command = argv[1];
    const auto events = read_events(argv[2]);
    if (command == "replay") {
      auto result = replay(events, false);
      write_trades(argument_value(argc, argv, "--trades"), result.trades);
      write_orders(argument_value(argc, argv, "--orders"),
                   result.book.active_orders());
      std::cout << "events=" << events.size() << " trades=" << result.trades.size()
                << " active_orders=" << result.book.active_order_count() << '\n';
      return 0;
    }
    if (command == "benchmark") {
      auto result = replay(events, true);
      const auto seconds = result.elapsed_seconds;
      const auto throughput = static_cast<double>(events.size()) / seconds;
      const auto p50 = percentile(result.latencies_ns, 0.50);
      const auto p95 = percentile(result.latencies_ns, 0.95);
      const auto p99 = percentile(result.latencies_ns, 0.99);
      std::ofstream output(argument_value(argc, argv, "--csv"));
      output << "implementation,events,trades,active_orders,elapsed_seconds,"
                "throughput_per_second,p50_microseconds,p95_microseconds,"
                "p99_microseconds\n";
      output << "cpp," << events.size() << ',' << result.trades.size() << ','
             << result.book.active_order_count() << ',' << std::setprecision(12)
             << seconds << ',' << throughput << ',' << p50 << ',' << p95 << ','
             << p99 << '\n';
      std::cout << "events/s=" << std::fixed << std::setprecision(0) << throughput
                << " p50_us=" << std::setprecision(3) << p50
                << " p95_us=" << p95 << " p99_us=" << p99 << '\n';
      return 0;
    }
    usage();
    return 2;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
