from app.facebook.feed import FacebookFeedPublisher
from app.facebook.reels import FacebookReelPublisher
from app.facebook.stories import FacebookStoryPublisher


def test_feed_publisher_dry_run():
    pub = FacebookFeedPublisher()
    pub.dry_run = True
    res = pub.publish_image_post("non_existent.jpg", "Test caption")
    assert res["success"] is True
    assert res["dry_run"] is True


def test_reel_publisher_dry_run():
    pub = FacebookReelPublisher()
    pub.dry_run = True
    res = pub.publish_reel("non_existent.mp4", "Test reel caption")
    assert res["success"] is True
    assert res["dry_run"] is True


def test_story_publisher_dry_run():
    pub = FacebookStoryPublisher()
    pub.dry_run = True
    res = pub.publish_story("non_existent.jpg", media_type="image")
    assert res["success"] is True
    assert res["dry_run"] is True
