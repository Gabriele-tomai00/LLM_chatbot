import re
from scrapy.dupefilters import RFPDupeFilter

class UnitsLinguisticDupeFilter(RFPDupeFilter):
    """
    Custom filter to handle language duplicates.
    Fixes the 'can't concat str to bytes' error by hex-encoding the fingerprint.
    """

    def __init__(self, path, debug, fingerprinter):
        super().__init__(path, debug)
        self.fingerprinter = fingerprinter

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        debug = settings.getbool('DUPEFILTER_DEBUG')
        path = settings.get('JOBDIR')
        return cls(path, debug, crawler.request_fingerprinter)

    def request_fingerprint(self, request):
        # 1. Normalize the URL
        url = request.url.replace(':443', '')
        # Remove /it/ or /en/ language prefixes
        url = re.sub(r'/(it|en)(/|$)', '/', url)
        # Remove trailing slash
        url = url.rstrip('/')

        # 2. Create a temporary request for hashing
        new_request = request.replace(url=url)

        # 3. Generate fingerprint (bytes) and convert to hex (string)
        # This solves: TypeError: can't concat str to bytes
        fp_bytes = self.fingerprinter.fingerprint(new_request)
        return fp_bytes.hex()