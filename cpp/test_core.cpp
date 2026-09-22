#include "core.hpp"
#include <cassert>
#include <iostream>
using namespace redline;
int main() {
    Book book;
    book.submit("first", false, 10, 101, false);
    book.submit("second", false, 10, 101, false);
    book.replace("first", 15, 0);
    auto trades = book.submit("buyer", true, 12, 0, true);
    assert(trades.size() == 2);
    assert(trades[0].maker == "second" && trades[0].quantity == 10);
    assert(trades[1].maker == "first" && trades[1].quantity == 2);
    book.check();
    auto before = book.active();
    try { book.replace("first", 0, 101); assert(false); }
    catch (const std::invalid_argument&) {}
    assert(book.get("first")->remaining == before[0].remaining);
    for (int i = 0; i < 10000; ++i) {
        auto id = "stress-" + std::to_string(i);
        book.submit(id, true, 10, 99, false);
        book.replace(id, 20, 98);
        book.cancel(id);
    }
    book.submit("cleanup", false, 1, 0, true);
    book.check();
    std::cout << "Native core checks passed\n";
}
