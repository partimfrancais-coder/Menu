import copy
import json
from pathlib import Path
import test_hosted


class RestaurantDataTests(test_hosted.HostedTests):
    def test_product_code_roundtrip_preserves_text_and_can_be_cleared(self):
        self.login();data=self.call('/api/menus').json
        pid=data['restaurants'][0]['categories'][0]['items'][0]['productId']
        item=next(p for p in data['products'] if p['id']==pid)
        item['productCode']='001-KOI/A'
        self.assertEqual(self.call('/api/menus','POST',json=data).status_code,200)
        saved=self.call('/api/menus').json
        self.assertEqual(saved['restaurants'][0]['categories'][0]['items'][0]['productCode'],'001-KOI/A')
        url=f"/api/restaurants/{data['restaurants'][0]['id']}/data"
        exported=self.call(url).json
        self.assertEqual(exported['restaurant']['categories'][0]['items'][0]['productCode'],'001-KOI/A')
        result=self.call(url,'POST',json={'revision':saved['revision'],'upload':exported})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['restaurants'][0]['categories'][0]['items'][0]['productCode'],'001-KOI/A')
        changed=self.call('/api/menus').json
        next(p for p in changed['products'] if p['id']==pid)['productCode']=''
        self.assertEqual(self.call('/api/menus','POST',json=changed).status_code,200)
        self.assertEqual(self.call(url).json['restaurant']['categories'][0]['items'][0]['productCode'],'')

    def test_invalid_product_code_rejected_without_changes(self):
        self.login();before=self.call('/api/menus').json
        for value in [12,None,{},'x'*101]:
            changed=copy.deepcopy(before)
            changed['restaurants'][0]['categories'][0]['items'][0]['productCode']=value
            self.assertEqual(self.call('/api/menus','POST',json=changed).status_code,400)
        self.assertEqual(self.call('/api/menus').json,before)

    def test_download_and_full_replacement_preserve_other_restaurant(self):
        self.login();before=self.call('/api/menus').json
        rid=before['restaurants'][0]['id'];url=f'/api/restaurants/{rid}/data'
        exported=self.call(url).json
        self.assertEqual(exported['restaurant'],before['restaurants'][0])
        replacement=copy.deepcopy(exported)
        replacement['restaurant']['categories']=[]
        replacement['restaurant']['logo']=''
        replacement['restaurant'].pop('tagCatalog',None)
        replacement['restaurant'].pop('designPrompt',None)
        res=self.call(url,'POST',json={'revision':before['revision'],'upload':replacement})
        self.assertEqual(res.status_code,200)
        current=self.call('/api/menus').json
        self.assertEqual(current['restaurants'][1],before['restaurants'][1])
        self.assertEqual(current['restaurants'][0]['categories'],[])
        self.assertEqual(current['restaurants'][0]['tagCatalog'],current['productTags'])
        self.assertEqual(current['restaurants'][0]['designPrompt'],'')
        previous=json.loads((Path(self.temp.name)/'menus.previous.json').read_text(encoding='utf-8'))
        self.assertEqual(previous['restaurants'][0],current['restaurants'][0])
        self.assertEqual(current['revision'],before['revision']+1)

    def test_invalid_or_conflicting_upload_leaves_data_untouched(self):
        self.login();before=self.call('/api/menus').json
        url=f"/api/restaurants/{before['restaurants'][0]['id']}/data"
        exported=self.call(url).json
        self.assertEqual(self.call(url,'POST',json={'revision':-1,'upload':exported}).status_code,409)
        exported['restaurant']['categories'][0]['items'][0]['price']=-5
        self.assertEqual(self.call(url,'POST',json={'revision':before['revision'],'upload':exported}).status_code,400)
        self.assertEqual(self.call(url,'POST',json={'revision':before['revision'],'upload':before}).status_code,400)
        self.assertEqual(self.call('/api/menus').json,before)

    def test_anonymous_and_cross_origin_replacement_denied(self):
        self.assertEqual(self.call('/api/restaurants/any/data').status_code,401)
        self.assertEqual(self.call('/api/restaurants/any/data','POST',json={}).status_code,401)
        self.login()
        self.assertEqual(self.client.post('/api/restaurants/any/data',base_url='https://menu.test',headers={'Origin':'https://evil.test'},json={}).status_code,403)
