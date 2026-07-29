#include "redline/order_book.hpp"

#include <iostream>
#include <stdexcept>

using redline::LimitOrderBook;
using redline::Side;

void require(bool condition, const char* message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

void test_price_time_priority_and_partial_fill() {
  LimitOrderBook book("TEST");
  book.submit_limit("ask-old", Side::Sell, 5, 10'100);
  book.submit_limit("ask-new", Side::Sell, 8, 10'100);
  const auto trades = book.submit_market("buyer", Side::Buy, 9);
  require(trades.size() == 2, "expected two fills");
  require(trades[0].maker_order_id == "ask-old", "old order must fill first");
  require(trades[0].quantity == 5, "old order must fill completely");
  require(trades[1].maker_order_id == "ask-new", "new order must fill second");
  require(trades[1].quantity == 4, "new order fill quantity is wrong");
  require(book.get_order("ask-new")->remaining == 4,
          "partial-fill remainder is wrong");
  book.assert_invariants();
}

void test_reduction_keeps_priority() {
  LimitOrderBook book("TEST");
  book.submit_limit("first", Side::Sell, 10, 10'100);
  book.submit_limit("second", Side::Sell, 10, 10'100);
  const auto original_sequence = book.get_order("first")->sequence;
  book.replace("first", 5);
  require(book.get_order("first")->sequence == original_sequence,
          "same-price reduction must retain priority");
  const auto trades = book.submit_market("buyer", Side::Buy, 7);
  require(trades[0].maker_order_id == "first", "reduced order lost priority");
  require(trades[1].maker_order_id == "second", "second fill is wrong");
}

void test_increase_loses_priority_and_cancel_is_lazy_safe() {
  LimitOrderBook book("TEST");
  book.submit_limit("first", Side::Buy, 5, 10'000);
  book.submit_limit("second", Side::Buy, 5, 10'000);
  book.replace("first", 8);
  book.cancel("second");
  book.submit_limit("third", Side::Buy, 5, 10'000);
  const auto trades = book.submit_market("seller", Side::Sell, 10);
  require(trades[0].maker_order_id == "first", "replacement priority is wrong");
  require(trades[0].quantity == 8, "replacement fill quantity is wrong");
  require(trades[1].maker_order_id == "third", "stale cancel reference matched");
  require(trades[1].quantity == 2, "third-order fill quantity is wrong");
  book.assert_invariants();
}

void test_better_price_executes_first() {
  LimitOrderBook book("TEST");
  book.submit_limit("ask-high", Side::Sell, 5, 10'200);
  book.submit_limit("ask-low", Side::Sell, 5, 10'100);
  const auto trades = book.submit_limit("buyer", Side::Buy, 5, 10'200);
  require(trades.size() == 1, "expected one fill");
  require(trades[0].maker_order_id == "ask-low",
          "better price did not execute first");
  require(trades[0].price_ticks == 10'100, "resting execution price is wrong");
}

int main() {
  test_price_time_priority_and_partial_fill();
  test_reduction_keeps_priority();
  test_increase_loses_priority_and_cancel_is_lazy_safe();
  test_better_price_executes_first();
  std::cout << "all C++ engine tests passed\n";
}
