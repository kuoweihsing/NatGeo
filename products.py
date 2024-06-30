import scrapy
import json

class ProductsSpider(scrapy.Spider):
    name = "products"
    allowed_domains = ["www.natgeostore.com.tw"]
    start_urls = ["https://www.natgeostore.com.tw"]

    def parse(self, response):
        meta = response.meta
        categories = response.xpath('//*[@id="shopline-section-header"]/nav[1]/div/div[1]/ul[2]/li/ul/li[*]')
        for cate in categories:
            meta['cate1Name'] = cate.css('a ::text').get().strip()
            meta['cate1Url'] = cate.css('a ::attr(href)').get().strip()
            if meta['cate1Name'] in ['會員優惠', '❄FROZEN涼感科技']:
                pass
            else:
                subcategories = cate.css('ul li')
                for subcate in subcategories:
                    meta['cate2Name'] = subcate.css('a ::text').get().strip()
                    meta['cate2Url'] = subcate.css('a ::attr(href)').get().strip()
                    meta['page'] = 1
                    url = meta['cate2Url'] + '?page={}&sort_by=created_at&order_by=desc&limit=72'.format(meta['page'])
                    yield scrapy.Request(url=url, callback=self.parse_products, meta=meta, dont_filter=True)

    def parse_products(self, response):
        meta = response.meta
        products = response.css('div[class="productList__product"]')
        for prod in products:
            meta['productId'] = prod.css('::attr(product-id)').get().strip()
            meta['saleUrl'] = prod.css('div[class="product-item"] a::attr(href)').get().strip()
            data = prod.css('div[class="product-item"] a::attr(ga-product)').get().strip()
            data = json.loads(data)
            meta['dealId'] = data['sku'].strip()
            meta['dealName'] = data['title'].strip()
            variations = json.loads(data['variations'])
            for var in variations:
                meta['skuId'] = var['key'].strip()
                meta['optionId'] = var['sku'].strip()
                meta['optionName'] = var['fields_translations']['zh-hant'][0].strip()
                meta['salePrice'] = prod.css('div[class="product-item"] a div[class*="info-box"] div[class="info-box-inner-wrapper"] div[class*="quick-cart-price"] div ::text').get().strip().replace(',', '').replace('NT$', '')
                url = 'https://www.natgeostore.com.tw/api/merchants/637c859dd14052009b051c6e/products/{}/check_stock?variation_id={}'.format(meta['productId'], meta['skuId'])
                yield scrapy.Request(url=url, callback=self.parse_stocks, meta=meta, dont_filter=True)
        if len(products) == 72:
            meta['page'] += 1
            url = meta['cate2Url'] + '?page={}&sort_by=created_at&order_by=desc&limit=72'.format(meta['page'])
            yield scrapy.Request(url=url, callback=self.parse_products, meta=meta, dont_filter=True)

    def parse_stocks(self, response):
        meta = response.meta
        data = json.loads(response.text)
        meta['totalStock'] = data['quantity']
        meta['orderableStock'] = data['total_orderable_quantity']
        meta['isSoldout'] = 1 if meta['orderableStock'] <= 0 else 0
        yield {
            'cate1Name': meta['cate1Name'],
            'cate2Name': meta['cate2Name'],
            'productId': meta['productId'],
            'skuId': meta['skuId'],
            'saleUrl': meta['saleUrl'],
            'dealId': meta['dealId'],
            'dealName': meta['dealName'],
            'optionId': meta['optionId'],
            'optionName': meta['optionName'],
            'salePrice': meta['salePrice'],
            'totalStock': meta['totalStock'],
            'orderableStock': meta['orderableStock'],
            'isSoldout': meta['isSoldout'],
            'page': meta['page']
        }
