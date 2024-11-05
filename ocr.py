from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='en') # need to run only once to load model into memory

def run_ocr(img_path):
    result = ocr.ocr(img_path, det=True, cls=True)
    ret = []
    for idx in range(len(result)):
        res = result[idx]
        for line in res:
            print(line[1][0])
            ret.append(line[1][0])
    return ret