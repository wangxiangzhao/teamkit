import pytest
from teamkit.visual import compare_images, optimize_image
Image=pytest.importorskip('PIL.Image')


def test_screenshots(tmp_path):
    a,b,c=(tmp_path/n for n in ['a.png','b.png','c.png'])
    Image.new('RGBA',(20,20),(10,20,30,255)).save(a)
    Image.new('RGBA',(20,20),(10,20,30,255)).save(b)
    Image.new('RGBA',(20,20),(200,20,30,255)).save(c)
    assert compare_images(a,b)['status']=='passed'
    assert compare_images(a,c,tolerance=.01)['status']=='failed'
    with pytest.raises(ValueError):
        compare_images(a,b,tolerance=-1)


def test_optimize_is_non_destructive(tmp_path):
    a=tmp_path/'source.png';b=tmp_path/'target.png'
    Image.new('RGB',(100,100),(5,6,7)).save(a)
    original=a.read_bytes()
    assert optimize_image(a,b)['status']=='dry-run'
    assert not b.exists()
    assert optimize_image(a,b,approve=True)['status']=='completed'
    assert a.read_bytes()==original
    assert b.exists()
    with pytest.raises(FileExistsError):
        optimize_image(a,b,approve=True)
