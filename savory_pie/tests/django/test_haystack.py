import unittest

import mock

from django.db import models

from savory_pie.formatters import JSONFormatter
from savory_pie.django.haystack_filter import HaystackFilter
from savory_pie.django.haystack_resources import HaystackSearchResource
from savory_pie.django.haystack_field import HaystackField
from savory_pie.tests.mock_context import mock_context
from test_filters import Params


class TestModel(models.Model):
    pass


class TestSearchResource(HaystackSearchResource):
    model_class = TestModel


class HaystackFilterTest(unittest.TestCase):

    @mock.patch('savory_pie.django.haystack_filter.SearchQuerySet')
    def test_simple_filter(self, haystack_qs_cls):
        result1 = mock.Mock(name='result1', pk=1)
        result2 = mock.Mock(name='result2', pk=2)

        haystack_qs = haystack_qs_cls.return_value
        haystack_qs.filter.return_value = haystack_qs
        haystack_qs.models.return_value = haystack_qs
        haystack_qs.__iter__ = lambda x: iter([result1, result2])

        queryset = mock.Mock(name='queryset')
        queryset.model = TestModel

        haystack_filter = HaystackFilter()
        haystack_filter.filter(
            mock_context(),
            Params({'q': 'foo'}),
            queryset,
        )

        queryset.assert_has_calls(
            [
                mock.call.filter(pk__in=[1, 2]),
            ],
            any_order=True,
        )

        haystack_qs.assert_has_calls(
            [
                mock.call.models(TestModel),
                mock.call.filter(content=u'foo'),
            ],
            any_order=True
        )

    @mock.patch('savory_pie.django.haystack_filter.SearchQuerySet')
    def test_multi_word_filter(self, haystack_qs_cls):
        haystack_qs = haystack_qs_cls.return_value
        haystack_qs.filter.return_value = haystack_qs
        haystack_qs.models.return_value = haystack_qs

        queryset = mock.Mock(name='queryset')
        queryset.model = TestModel

        haystack_filter = HaystackFilter()
        haystack_filter.filter(
            mock_context(),
            Params({'q': 'foo bar baz'}),
            queryset,
        )

        haystack_qs.assert_has_calls(
            [
                mock.call.filter(content=u'foo'),
                mock.call.filter(content=u'bar'),
                mock.call.filter(content=u'baz'),
                mock.call.models(TestModel),
            ],
            any_order=True
        )


class HaystackFieldTest(unittest.TestCase):

    def test_haystack_field(self):
        FooResource = mock.Mock()
        FooResource.return_value = frv = mock.Mock()
        frv.get.return_value = {'a': 'b'}
        api = HaystackField(
            formatter=JSONFormatter(),
            resource=FooResource)
        self.assertEqual(api.prepare(None), '{"a": "b", "$stale": true}')


class HaystackSearchResourceTest(unittest.TestCase):

    @mock.patch('savory_pie.django.haystack_resources.SearchQuerySet')
    def test_haystack_search_resource(self, haystack_qs_cls):
        n = 3
        haystack_qs_cls.return_value = haystack_qs = mock.Mock()
        haystack_qs.filter.return_value = haystack_qs
        haystack_qs.models.return_value = haystack_qs
        haystack_qs.count.return_value = n
        result = mock.Mock()
        result.get_stored_fields.return_value = {'api': '"api-as-string"'}
        haystack_qs.__iter__ = mock.Mock(return_value=(result for i in range(n)))

        sr = HaystackSearchResource()
        sr.model_class = TestModel
        ctx = mock.Mock(base_uri='foo')
        self.assertEqual(
            ''.join([x for x in sr.get(ctx, {'q': 'foo'})]),
            '{"meta":{"count":3},"objects":["api-as-string","api-as-string","api-as-string"]}')
        haystack_qs.models.assert_called_with(TestModel)
        haystack_qs.count.assert_called_with()

    @mock.patch('savory_pie.django.haystack_resources.SearchQuerySet')
    def test_all_results(self, SearchQuerySet):
        ctx = mock.Mock(base_uri='foo')

        result1 = mock.Mock()
        result1.get_stored_fields.return_value = {'api': '{"json":1}'}

        result2 = mock.Mock()
        result2.get_stored_fields.return_value = {'api': '{"json":2}'}

        qs = SearchQuerySet.return_value
        qs.models.return_value = qs
        qs.filter.return_value = qs
        qs.__iter__ = mock.Mock(return_value=iter([result1, result2]))
        qs.count.return_value = 2

        resource = TestSearchResource()
        result = resource.get(ctx, {})
        print result

        self.assertEqual(
            ''.join(result),
            '{"meta":{"count":2},"objects":[{"json":1},{"json":2}]}'
        )

        self.assertTrue(ctx.streaming_response)
        qs.assert_has_call(
            mock.call.models(TestModel),
            any_order=True,
        )

    @mock.patch('savory_pie.django.haystack_resources.SearchQuerySet')
    def test_q_filter(self, SearchQuerySet):
        ctx = mock.Mock(base_uri='foo')

        qs = SearchQuerySet.return_value
        qs.models.return_value = qs
        qs.filter.return_value = qs
        qs.__iter__ = mock.Mock(return_value=iter([]))
        qs.count.return_value = 0

        resource = TestSearchResource()
        result = resource.get(ctx, {'q': 'foo bar'})
        print result

        self.assertEqual(
            ''.join(result),
            '{"meta":{"count":0},"objects":[]}'
        )

        qs.assert_has_call(
            mock.call.filter('foo'),
            mock.call.filter('bar'),
            any_order=True,
        )

    @mock.patch('savory_pie.django.haystack_resources.SearchQuerySet')
    def test_updated_filter(self, SearchQuerySet):
        ctx = mock.Mock(base_uri='foo')

        qs = SearchQuerySet.return_value
        qs.models.return_value = qs
        qs.filter.return_value = qs
        qs.__iter__ = mock.Mock(return_value=iter([]))
        qs.count.return_value = 0

        resource = TestSearchResource()
        result = resource.get(ctx, {'updatedSince': '2012-01-01'})
        print result

        self.assertEqual(
            ''.join(result),
            '{"meta":{"count":0},"objects":[]}'
        )

        qs.assert_has_call(
            mock.call.filter('2012-01-01'),
            any_order=True,
        )