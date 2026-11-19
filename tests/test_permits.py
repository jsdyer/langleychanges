import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import permits


class PermitTests(unittest.TestCase):
    def setUp(self):
        self.rows = [('BP12', '1 A ST', '2020-01-10', 'Building', 'Addition'),
                     ('BP12', '3 A ST', '2020-01-10', 'Building', 'Addition')]
        self.folders = permits.group_folders(self.rows)

    def test_groups_multiple_addresses_and_rejects_changed_identity(self):
        self.assertEqual(self.folders['BP12']['addresses'], ['1 A ST', '3 A ST'])
        self.assertEqual(self.folders['BP12']['descriptions'], ['Addition'])
        with self.assertRaisesRegex(ValueError, 'Conflicting rows'):
            permits.group_folders(self.rows + [('BP12', '1 A ST', '2020-01-11', 'Building', 'Addition')])

    def test_last_seen_first_absent_and_return_keep_observations(self):
        def observe(folders, records, date):
            return permits.reconcile(folders, {'records': records}, date)
        first = observe(self.folders, [], '2026-01-01')
        second = observe(self.folders, first, '2026-01-02')
        absent = observe({}, second, '2026-01-04')
        still_absent = observe({}, absent, '2026-01-05')
        returned = observe(self.folders, still_absent, '2026-01-06')
        self.assertEqual(first[0]['periods'][0]['last_seen'], '2026-01-01')
        self.assertEqual(returned[0]['periods'], [
            {'first_seen':'2026-01-01','last_seen':'2026-01-02','first_absent':'2026-01-04'},
            {'first_seen':'2026-01-06','last_seen':'2026-01-06'}])
        self.assertEqual(still_absent, absent)

    def test_crawl_rejects_partially_returned_page(self):
        from io import BytesIO
        from urllib.parse import parse_qs
        def response(page):
            size = 1 if page == 2 else 2
            def link(target):
                return f'<a href="javascript:__doPostBack(\'gvPermitList\',\'Page${target}\')">{target}</a>'
            return BytesIO(('<form id="form1"><input type="hidden" name="__VIEWSTATE" value="s">'
                '<input type="hidden" name="__EVENTVALIDATION" value="v"><table id="gvPermitList">'
                + '<tr>' + ''.join(f'<th>{c}</th>' for c in permits.HEADINGS) + '</tr>'
                + ''.join(f'<tr><td>BP{page}{i}</td><td>1 ST</td><td>Jan-10-2020</td>'
                          '<td>Building</td><td></td><td>Addition</td></tr>' for i in range(size))
                + f'<tr class="myPager"><td><span>{page}</span>'
                + ''.join(link(t) for t in ([2,'Last'] if page == 1 else [1,2] if page == 3 else [1,3,'Last']))
                + '</td></tr></table></form>').encode())
        def serve(request, timeout):
            target = parse_qs((request.data or b'').decode()).get('__EVENTARGUMENT', ['Page$1'])[0][5:]
            return response(3 if target == 'Last' else int(target))
        with patch.object(permits, 'build_opener') as mock_open:
            mock_open.return_value.open.side_effect = serve
            with self.assertRaisesRegex(ValueError, 'Short interior page'):
                permits.fetch_pages()


if __name__ == '__main__':
    unittest.main()
