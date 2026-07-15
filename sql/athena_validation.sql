SELECT mid, order_flag, tag_reserved_not_paid, order_id
FROM reservation_dm.dm_reservation_conversion
ORDER BY mid;

SELECT campaign_id, site, channel, reserved_users, paid_users,
       unconverted_users, conversion_rate
FROM reservation_ads.ads_campaign_conversion
ORDER BY channel;

SELECT mid, campaign_id, product_id, site, channel
FROM reservation_ads.ads_crm_reserved_not_paid
ORDER BY mid;
