#include "redline/order_book.hpp"

#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <utility>

namespace redline {

namespace {

std::string uppercase(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(),
                 [](unsigned char character) {
                   return static_cast<char>(std::toupper(character));
                 });
  return value;
}

}  // namespace

LimitOrderBook::LimitOrderBook(std::string symbol, bool retain_trade_history)
    : symbol_(uppercase(std::move(symbol))),
      retain_trade_history_(retain_trade_history) {
  if (symbol_.empty()) {
    throw std::invalid_argument("symbol cannot be empty");
  }
}

std::vector<Trade> LimitOrderBook::submit_limit(const std::string& order_id,
                                                Side side,
                                                std::int64_t quantity,
                                                std::int64_t price_ticks) {
  if (price_ticks <= 0) {
    throw std::invalid_argument("price_ticks must be positive");
  }
  auto order = new_order(order_id, side, OrderType::Limit, quantity, price_ticks);
  auto produced = match(order);
  if (order.remaining > 0) {
    rest(order);
  }
  return produced;
}

std::vector<Trade> LimitOrderBook::submit_market(const std::string& order_id,
                                                 Side side,
                                                 std::int64_t quantity) {
  auto order = new_order(order_id, side, OrderType::Market, quantity, std::nullopt);
  return match(order);
}

Order LimitOrderBook::cancel(const std::string& order_id) {
  const auto iterator = orders_.find(order_id);
  if (iterator == orders_.end()) {
    throw std::out_of_range("unknown active order: " + order_id);
  }
  const auto snapshot = iterator->second;
  orders_.erase(iterator);
  return snapshot;
}

std::vector<Trade> LimitOrderBook::replace(
    const std::string& order_id, std::int64_t new_quantity,
    std::optional<std::int64_t> new_price_ticks) {
  if (new_quantity <= 0) {
    throw std::invalid_argument("new_quantity must be positive; use cancel instead");
  }
  const auto iterator = orders_.find(order_id);
  if (iterator == orders_.end()) {
    throw std::out_of_range("unknown active order: " + order_id);
  }

  auto order = iterator->second;
  const auto price_ticks = new_price_ticks.value_or(order.price_ticks.value());
  if (price_ticks <= 0) {
    throw std::invalid_argument("new_price_ticks must be positive");
  }
  const bool same_price = price_ticks == order.price_ticks.value();
  if (same_price && new_quantity <= order.remaining) {
    const auto filled = order.quantity - order.remaining;
    iterator->second.quantity = filled + new_quantity;
    iterator->second.remaining = new_quantity;
    return {};
  }

  orders_.erase(iterator);
  const auto filled = order.quantity - order.remaining;
  order.quantity = filled + new_quantity;
  order.remaining = new_quantity;
  order.price_ticks = price_ticks;
  order.sequence = ++order_sequence_;
  max_total_quantity_[order_id] =
      std::max(max_total_quantity_.at(order_id), order.quantity);

  auto produced = match(order);
  if (order.remaining > 0) {
    rest(order);
  }
  return produced;
}

std::optional<Order> LimitOrderBook::get_order(const std::string& order_id) const {
  const auto iterator = orders_.find(order_id);
  if (iterator == orders_.end()) {
    return std::nullopt;
  }
  return iterator->second;
}

std::vector<Order> LimitOrderBook::active_orders() const {
  std::vector<Order> result;
  result.reserve(orders_.size());
  for (const auto& [order_id, order] : orders_) {
    static_cast<void>(order_id);
    result.push_back(order);
  }
  std::ranges::sort(result, {}, &Order::sequence);
  return result;
}

const std::vector<Trade>& LimitOrderBook::trade_history() const noexcept {
  return trades_;
}

std::vector<BookLevel> LimitOrderBook::depth(Side side, std::size_t levels) const {
  if (levels < 1) {
    throw std::invalid_argument("levels must be positive");
  }
  std::map<std::int64_t, BookLevel> aggregate;
  for (const auto& [order_id, order] : orders_) {
    static_cast<void>(order_id);
    if (order.side != side || !order.price_ticks.has_value()) {
      continue;
    }
    auto& level = aggregate.try_emplace(order.price_ticks.value(),
                                        BookLevel{order.price_ticks.value(), 0, 0})
                      .first->second;
    level.quantity += order.remaining;
    ++level.order_count;
  }

  std::vector<BookLevel> result;
  result.reserve(std::min(levels, aggregate.size()));
  if (side == Side::Buy) {
    for (auto iterator = aggregate.rbegin();
         iterator != aggregate.rend() && result.size() < levels; ++iterator) {
      result.push_back(iterator->second);
    }
  } else {
    for (auto iterator = aggregate.begin();
         iterator != aggregate.end() && result.size() < levels; ++iterator) {
      result.push_back(iterator->second);
    }
  }
  return result;
}

std::size_t LimitOrderBook::active_order_count() const noexcept {
  return orders_.size();
}

void LimitOrderBook::assert_invariants() const {
  for (const auto& [order_id, order] : orders_) {
    if (order_id != order.order_id) {
      throw std::logic_error("active-order key does not match order ID");
    }
    if (order.order_type != OrderType::Limit) {
      throw std::logic_error("market order is resting on the book");
    }
    if (!order.price_ticks.has_value() || order.price_ticks.value() <= 0) {
      throw std::logic_error("active order has an invalid price");
    }
    if (order.remaining <= 0 || order.remaining > order.quantity) {
      throw std::logic_error("active order has an invalid remaining quantity");
    }
  }
  const auto bid = depth(Side::Buy, 1);
  const auto ask = depth(Side::Sell, 1);
  if (!bid.empty() && !ask.empty()) {
    if (bid.front().price_ticks >= ask.front().price_ticks) {
      throw std::logic_error("book is crossed after matching");
    }
  }
  std::uint64_t last_sequence = 0;
  for (const auto& trade : trades_) {
    if (trade.sequence <= last_sequence) {
      throw std::logic_error("trade sequences are not strictly increasing");
    }
    if (trade.quantity <= 0 || trade.price_ticks <= 0) {
      throw std::logic_error("trade has an invalid quantity or price");
    }
    last_sequence = trade.sequence;
  }
}

Order LimitOrderBook::new_order(const std::string& order_id, Side side,
                                OrderType order_type, std::int64_t quantity,
                                std::optional<std::int64_t> price_ticks) {
  if (order_id.empty()) {
    throw std::invalid_argument("order_id cannot be empty");
  }
  if (seen_order_ids_.contains(order_id)) {
    throw std::invalid_argument("order_id has already been used: " + order_id);
  }
  if (quantity <= 0) {
    throw std::invalid_argument("quantity must be positive");
  }
  seen_order_ids_.insert(order_id);
  max_total_quantity_[order_id] = quantity;
  return Order{order_id, side, order_type, quantity, quantity, ++order_sequence_,
               price_ticks};
}

std::vector<Trade> LimitOrderBook::match(Order& incoming) {
  std::vector<Trade> produced;
  while (incoming.remaining > 0) {
    auto* resting = best_opposite(incoming.side);
    if (resting == nullptr || !crosses(incoming, *resting)) {
      break;
    }
    const auto quantity = std::min(incoming.remaining, resting->remaining);
    incoming.remaining -= quantity;
    resting->remaining -= quantity;
    Trade trade{++trade_sequence_, symbol_, resting->price_ticks.value(), quantity,
                resting->order_id, incoming.order_id, incoming.side};
    produced.push_back(trade);
    if (retain_trade_history_) {
      trades_.push_back(trade);
    }
    if (resting->remaining == 0) {
      const auto resting_id = resting->order_id;
      const auto resting_side = resting->side;
      orders_.erase(resting_id);
      discard_stale_top(resting_side);
    }
  }
  return produced;
}

void LimitOrderBook::rest(const Order& order) {
  orders_.insert_or_assign(order.order_id, order);
  RestingRef reference{order.order_id, order.sequence};
  if (order.side == Side::Buy) {
    bids_[order.price_ticks.value()].push_back(std::move(reference));
  } else {
    asks_[order.price_ticks.value()].push_back(std::move(reference));
  }
}

Order* LimitOrderBook::best_opposite(Side incoming_side) {
  const auto opposite = incoming_side == Side::Buy ? Side::Sell : Side::Buy;
  discard_stale_top(opposite);
  if (opposite == Side::Sell) {
    if (asks_.empty()) {
      return nullptr;
    }
    return &orders_.at(asks_.begin()->second.front().order_id);
  }
  if (bids_.empty()) {
    return nullptr;
  }
  return &orders_.at(bids_.begin()->second.front().order_id);
}

void LimitOrderBook::discard_stale_top(Side side) {
  if (side == Side::Buy) {
    while (!bids_.empty()) {
      auto level = bids_.begin();
      while (!level->second.empty() &&
             !is_live(level->second.front(), side, level->first)) {
        level->second.pop_front();
      }
      if (!level->second.empty()) {
        return;
      }
      bids_.erase(level);
    }
    return;
  }
  while (!asks_.empty()) {
    auto level = asks_.begin();
    while (!level->second.empty() &&
           !is_live(level->second.front(), side, level->first)) {
      level->second.pop_front();
    }
    if (!level->second.empty()) {
      return;
    }
    asks_.erase(level);
  }
}

bool LimitOrderBook::crosses(const Order& incoming, const Order& resting) const {
  if (incoming.order_type == OrderType::Market) {
    return true;
  }
  if (incoming.side == Side::Buy) {
    return incoming.price_ticks.value() >= resting.price_ticks.value();
  }
  return incoming.price_ticks.value() <= resting.price_ticks.value();
}

bool LimitOrderBook::is_live(const RestingRef& ref, Side side,
                             std::int64_t price_ticks) const {
  const auto iterator = orders_.find(ref.order_id);
  return iterator != orders_.end() && iterator->second.sequence == ref.sequence &&
         iterator->second.side == side && iterator->second.remaining > 0 &&
         iterator->second.price_ticks == price_ticks;
}

std::string to_string(Side side) { return side == Side::Buy ? "BUY" : "SELL"; }

Side parse_side(const std::string& text) {
  const auto normalized = uppercase(text);
  if (normalized == "BUY") {
    return Side::Buy;
  }
  if (normalized == "SELL") {
    return Side::Sell;
  }
  throw std::invalid_argument("invalid side: " + text);
}

}  // namespace redline
