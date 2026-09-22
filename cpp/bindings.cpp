#include "core.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
using namespace redline;
PYBIND11_MODULE(_native, m) {
    py::class_<Order>(m, "Order")
        .def_readonly("id", &Order::id).def_readonly("buy", &Order::buy)
        .def_readonly("quantity", &Order::quantity).def_readonly("remaining", &Order::remaining)
        .def_readonly("sequence", &Order::sequence).def_readonly("price", &Order::price);
    py::class_<Trade>(m, "Trade")
        .def_readonly("sequence", &Trade::sequence).def_readonly("price", &Trade::price)
        .def_readonly("quantity", &Trade::quantity).def_readonly("maker", &Trade::maker)
        .def_readonly("taker", &Trade::taker).def_readonly("buy", &Trade::buy);
    py::class_<Level>(m, "Level")
        .def_readonly("price", &Level::price).def_readonly("quantity", &Level::quantity).def_readonly("count", &Level::count);
    py::class_<Book>(m, "Book").def(py::init<bool>())
        .def("submit", &Book::submit).def("cancel", &Book::cancel)
        .def("replace", &Book::replace).def("active", &Book::active)
        .def("get", &Book::get).def("check", &Book::check)
        .def("history", &Book::history).def("count", &Book::count).def("depth", &Book::depth);
    m.attr("compiler") = __VERSION__;
}
