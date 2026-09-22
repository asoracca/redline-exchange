#pragma once
#include <algorithm>
#include <cstdint>
#include <map>
#include <queue>
#include <optional>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace redline {
using Int = std::int64_t;
// Bounded integers keep arithmetic portable and leave ample headroom for counters.
constexpr Int max_value = (Int{1} << 53) - 1;
struct Order {
    std::string id;
    bool buy;
    Int quantity, remaining, sequence, price;
};
struct Trade {
    Int sequence, price, quantity;
    std::string maker, taker;
    bool buy;
};
struct Level { Int price, quantity, count; };
class Book {
    using Entry = std::tuple<Int, Int, std::string>;
    using Heap = std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>>;
    Heap bids_, asks_;
    std::unordered_map<std::string, Order> orders_;
    std::unordered_set<std::string> seen_;
    std::unordered_map<std::string, Int> max_quantity_;
    std::vector<Trade> history_;
    Int sequence_ = 0, trade_sequence_ = 0;
    bool retain_;
    static Entry entry(const Order& o) { return {o.buy ? -o.price : o.price, o.sequence, o.id}; }
    Heap& heap(bool buy) { return buy ? bids_ : asks_; }
    Order* best(bool buy) {
        auto& h = heap(buy);
        while (!h.empty()) {
            auto it = orders_.find(std::get<2>(h.top()));
            if (it != orders_.end() && entry(it->second) == h.top()) return &it->second;
            h.pop();
        }
        return nullptr;
    }
    void rest(const Order& o) { orders_.emplace(o.id, o); heap(o.buy).push(entry(o)); }
    std::vector<Trade> match(Order& incoming) {
        std::vector<Trade> trades;
        while (incoming.remaining) {
            auto* maker = best(!incoming.buy);
            if (!maker || (incoming.price && (incoming.buy ? incoming.price < maker->price : incoming.price > maker->price))) break;
            Int quantity = std::min(incoming.remaining, maker->remaining);
            incoming.remaining -= quantity;
            maker->remaining -= quantity;
            Trade t{++trade_sequence_, maker->price, quantity, maker->id, incoming.id, incoming.buy};
            trades.push_back(t);
            if (retain_) history_.push_back(t);
            if (!maker->remaining) orders_.erase(t.maker);
        }
        return trades;
    }
    static void positive(Int value) {
        if (value <= 0 || value > max_value) throw std::invalid_argument("quantity/price outside supported range");
    }
public:
    explicit Book(bool retain = true) : retain_(retain) {}
    std::vector<Trade> submit(const std::string& id, bool buy, Int quantity, Int price, bool market) {
        positive(quantity);
        if (!market) positive(price);
        if (id.empty() || id.find_first_not_of(" \t\r\n") == std::string::npos) throw std::invalid_argument("empty order ID");
        if (seen_.count(id)) throw std::invalid_argument("order ID already used");
        Order o{id, buy, quantity, quantity, ++sequence_, market ? 0 : price};
        seen_.insert(id);
        max_quantity_[id] = quantity;
        auto trades = match(o);
        if (!market && o.remaining) rest(o);
        return trades;
    }
    Order cancel(const std::string& id) {
        auto it = orders_.find(id);
        if (it == orders_.end()) throw std::out_of_range("unknown active order");
        auto o = it->second;
        orders_.erase(it);
        return o;
    }
    std::vector<Trade> replace(const std::string& id, Int quantity, Int price) {
        positive(quantity);
        auto it = orders_.find(id);
        if (it == orders_.end()) throw std::out_of_range("unknown active order");
        Order o = it->second;
        if (!price) price = o.price;
        positive(price);
        Int filled = o.quantity - o.remaining;
        if (quantity > max_value - filled) throw std::invalid_argument("total quantity outside supported range");
        if (price == o.price && quantity <= o.remaining) {
            it->second.quantity = filled + quantity;
            it->second.remaining = quantity;
            return {};
        }
        orders_.erase(it);
        o.quantity = filled + quantity;
        o.remaining = quantity;
        o.price = price;
        o.sequence = ++sequence_;
        max_quantity_[id] = std::max(max_quantity_[id], o.quantity);
        auto trades = match(o);
        if (o.remaining) rest(o);
        return trades;
    }
    std::optional<Order> get(const std::string& id) const {
        auto it = orders_.find(id);
        if (it == orders_.end()) return std::nullopt;
        return it->second;
    }
    void check() const {
        auto require = [](bool value) { if (!value) throw std::logic_error("book invariant violated"); };
        std::unordered_set<std::string> present;
        for (auto h : {bids_, asks_}) {
            while (!h.empty()) {
                auto it = orders_.find(std::get<2>(h.top()));
                if (it != orders_.end() && entry(it->second) == h.top()) present.insert(it->first);
                h.pop();
            }
        }
        for (const auto& p : orders_) {
            const auto& o = p.second;
            require(o.id == p.first && o.price > 0 && o.remaining > 0 && o.remaining <= o.quantity);
            require(present.count(o.id) && seen_.count(o.id));
        }
        auto bids = depth(true, 1), asks = depth(false, 1);
        require(bids.empty() || asks.empty() || bids.front().price < asks.front().price);
        std::unordered_map<std::string, Int> traded;
        Int last = 0;
        for (const auto& t : history_) {
            require(t.sequence > last && t.price > 0 && t.quantity > 0);
            last = t.sequence;
            traded[t.maker] += t.quantity; traded[t.taker] += t.quantity;
        }
        for (const auto& p : traded) require(p.second <= max_quantity_.at(p.first));
    }
    std::vector<Order> active() const {
        std::vector<Order> result;
        for (const auto& pair : orders_) result.push_back(pair.second);
        std::sort(result.begin(), result.end(), [](const Order& a, const Order& b){return a.sequence < b.sequence;});
        return result;
    }
    const std::vector<Trade>& history() const { return history_; }
    std::size_t count() const { return orders_.size(); }
    std::vector<Level> depth(bool buy, Int levels) const {
        if (levels < 1) throw std::invalid_argument("levels must be positive");
        std::map<Int, Level> prices;
        for (const auto& pair : orders_) {
            const auto& o = pair.second;
            if (o.buy != buy) continue;
            auto& l = prices[buy ? -o.price : o.price];
            l.price = o.price;
            // Do not silently wrap aggregate depth on large books.
            if (l.quantity > INT64_MAX - o.remaining) throw std::overflow_error("depth quantity overflow");
            l.quantity += o.remaining; ++l.count;
        }
        std::vector<Level> result;
        for (const auto& p : prices) { if (result.size() >= static_cast<std::size_t>(levels)) break; result.push_back(p.second); }
        return result;
    }
};
} // namespace redline
