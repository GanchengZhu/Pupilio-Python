# _*_ coding: utf-8 _*_
# Tests for the @deprecated decorator.

import warnings

import pytest

from pupilio.annotation import deprecated


class TestDeprecated:
    def test_warns_on_call(self):
        @deprecated("1.2.3")
        def old_function():
            return "result"

        with pytest.warns(DeprecationWarning):
            old_function()

    def test_does_not_warn_until_called(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")

            @deprecated("1.2.3")
            def old_function():
                return "result"

    def test_return_value_is_passed_through(self):
        @deprecated("1.2.3")
        def add(a, b):
            return a + b

        with pytest.warns(DeprecationWarning):
            assert add(2, 3) == 5

    def test_arguments_are_forwarded(self):
        received = {}

        @deprecated("1.2.3")
        def record(*args, **kwargs):
            received["args"] = args
            received["kwargs"] = kwargs

        with pytest.warns(DeprecationWarning):
            record(1, 2, key="value")

        assert received["args"] == (1, 2)
        assert received["kwargs"] == {"key": "value"}

    def test_exceptions_propagate(self):
        @deprecated("1.2.3")
        def boom():
            raise ValueError("boom")

        with pytest.warns(DeprecationWarning), pytest.raises(ValueError, match="boom"):
            boom()

    def test_identity_is_preserved_for_sphinx(self):
        # functools.wraps keeps the name and docstring, which the generated API
        # documentation depends on.
        @deprecated("1.2.3")
        def documented_function():
            """Original docstring."""

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "Original docstring."

    def test_version_appears_in_the_message(self):
        @deprecated("9.9.9")
        def old_function():
            pass

        with pytest.warns(DeprecationWarning, match="9.9.9"):
            old_function()

    def test_tips_appear_in_the_message(self):
        @deprecated("1.2.3", "Please use `new_function`")
        def old_function():
            pass

        with pytest.warns(DeprecationWarning, match="new_function"):
            old_function()

    def test_function_name_appears_in_the_message(self):
        @deprecated("1.2.3")
        def uniquely_named_function():
            pass

        with pytest.warns(DeprecationWarning, match="uniquely_named_function"):
            uniquely_named_function()

    def test_works_on_methods(self):
        class Tracker:
            @deprecated("1.2.3")
            def legacy(self):
                return "ok"

        with pytest.warns(DeprecationWarning):
            assert Tracker().legacy() == "ok"

    def test_composes_under_property(self):
        # core.Pupilio stacks @property above @deprecated; the reverse order
        # silently produces a non-callable attribute instead of a property.
        class Tracker:
            @property
            @deprecated("1.2.3")
            def legacy(self):
                return "value"

        with pytest.warns(DeprecationWarning):
            assert Tracker().legacy == "value"
