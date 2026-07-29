#pragma once

#include <cstdint>
#include <deque>
#include <functional>
#include <map>
#include <optional>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace redline {

enum class Side { Buy, Sell };
enum class OrderType { Limit, Market };

struct Order {
  std::string order_id;
  Side side;
  OrderType order_type;
  std::int64_t quantity;
  std::int64_t remaining;
  std::uint64_t sequence;
  std::optional<std::int64_t> price_ticks;
};

struct Trade {
  std::uint64_t sequence;
  std::string symbol;
  std::int64_t price_ticks;
  std::int64_t quantity;
  std::string maker_order_id;
  std::string taker_order_id;
  Side taker_side;

  bool operator==(const Trade&) const = default;
};

struct BookLevel {
  std::int64_t price_ticks;
  std::int64_t quantity;
  std::size_t order_count;

  bool operator==(const BookLevel&) const = default;
};

class LimitOrderBook {
 public:
  explicit LimitOrderBook(std::string symbol, bool retain_trade_history = true);

  std::vector<Trade> submit_limit(const std::string& order_id, Side side,
                                  std::int64_t quantity, std::int64_t price_ticks);
  std::vector<Trade> submit_market(const std::string& order_id, Side side,
                                   std::int64_t quantity);
  Order cancel(const std::string& order_id);
  std::vector<Trade> replace(const std::string& order_id, std::int64_t new_quantity,
                             std::optional<std::int64_t> new_price_ticks = std::nullopt);

  [[nodiscard]] std::optional<Order> get_order(const std::string& order_id) const;
  [[nodiscard]] std::vector<Order> active_orders() const;
  [[nodiscard]] const std::vector<Trade>& trade_history() const noexcept;
  [[nodiscard]] std::vector<BookLevel> depth(Side side, std::size_t levels = 5) const;
  [[nodiscard]] std::size_t active_order_count() const noexcept;
  void assert_invariants() const;

 private:
  struct RestingRef {
    std::string order_id;
    std::uint64_t sequence;
  };

  using BidBook = std::map<std::int64_t, std::deque<RestingRef>, std::greater<>>;
  using AskBook = std::map<std::int64_t, std::deque<RestingRef>, std::less<>>;

  std::string symbol_;
  BidBook bids_;
  AskBook asks_;
  std::unordered_map<std::string, Order> orders_;
  std::unordered_set<std::string> seen_order_ids_;
  std::unordered_map<std::string, std::int64_t> max_total_quantity_;
  std::vector<Trade> trades_;
  bool retain_trade_history_;
  std::uint64_t order_sequence_{0};
  std::uint64_t trade_sequence_{0};

  Order new_order(const std::string& order_id, Side side, OrderType order_type,
                  std::int64_t quantity, std::optional<std::int64_t> price_ticks);
  std::vector<Trade> match(Order& incoming);
  void rest(const Order& order);
  Order* best_opposite(Side incoming_side);
  void discard_stale_top(Side side);
  [[nodiscard]] bool crosses(const Order& incoming, const Order& resting) const;
  [[nodiscard]] bool is_live(const RestingRef& ref, Side side,
                             std::int64_t price_ticks) const;
};

[[nodiscard]] std::string to_string(Side side);
[[nodiscard]] Side parse_side(const std::string& text);

}  // namespace redline
