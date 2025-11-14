'use client'

import { useEffect, useRef } from 'react'

interface AdPlayerProps {
  onAdComplete: () => void
  onAdError: () => void
}

declare global {
  interface Window {
    google: any
  }
}

export default function AdPlayer({ onAdComplete, onAdError }: AdPlayerProps) {
  const adContainerRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const adCompletedRef = useRef(false)

  useEffect(() => {
    if (!adContainerRef.current || !videoRef.current) return

    // Check if IMA SDK is loaded
    if (typeof window === 'undefined' || !window.google || !window.google.ima) {
      console.error('Google IMA SDK not loaded')
      onAdError()
      return
    }

    const adDisplayContainer = new window.google.ima.AdDisplayContainer(
      adContainerRef.current,
      videoRef.current
    )

    const adsLoader = new window.google.ima.AdsLoader(adDisplayContainer)

    // Event listeners
    adsLoader.addEventListener(
      window.google.ima.AdsManagerLoadedEvent.Type.ADS_MANAGER_LOADED,
      onAdsManagerLoaded,
      false
    )
    adsLoader.addEventListener(
      window.google.ima.AdErrorEvent.Type.AD_ERROR,
      onAdErrorEvent,
      false
    )

    function onAdsManagerLoaded(adsManagerLoadedEvent: any) {
      const adsRenderingSettings = new window.google.ima.AdsRenderingSettings()
      adsRenderingSettings.restoreCustomPlaybackStateOnAdBreakComplete = true

      const adsManager = adsManagerLoadedEvent.getAdsManager(
        videoRef.current,
        adsRenderingSettings
      )

      adsManager.addEventListener(
        window.google.ima.AdErrorEvent.Type.AD_ERROR,
        onAdErrorEvent
      )
      adsManager.addEventListener(
        window.google.ima.AdEvent.Type.CONTENT_PAUSE_REQUESTED,
        () => {
          if (videoRef.current) {
            videoRef.current.pause()
          }
        }
      )
      adsManager.addEventListener(
        window.google.ima.AdEvent.Type.CONTENT_RESUME_REQUESTED,
        () => {
          if (videoRef.current) {
            videoRef.current.play()
          }
        }
      )
      adsManager.addEventListener(
        window.google.ima.AdEvent.Type.ALL_ADS_COMPLETED,
        () => {
          if (!adCompletedRef.current) {
            adCompletedRef.current = true
            onAdComplete()
            adsManager.destroy()
          }
        }
      )
      adsManager.addEventListener(
        window.google.ima.AdEvent.Type.COMPLETE,
        () => {
          if (!adCompletedRef.current) {
            adCompletedRef.current = true
            onAdComplete()
          }
        }
      )

      try {
        adDisplayContainer.initialize()
        adsManager.init(640, 360, window.google.ima.ViewMode.NORMAL)
        adsManager.start()
      } catch (adError) {
        console.error('AdsManager error:', adError)
        if (videoRef.current) {
          videoRef.current.play()
        }
        onAdError()
      }
    }

    function onAdErrorEvent(adErrorEvent: any) {
      console.error('Ad error:', adErrorEvent.getError())
      onAdError()
      if (adsLoader) {
        adsLoader.destroy()
      }
    }

    // Request ads
    const adsRequest = new window.google.ima.AdsRequest()
    // Using Google's test ad tag for rewarded video
    adsRequest.adTagUrl = 'https://pubads.g.doubleclick.net/gampad/ads?iu=/21775744923/external/single_ad_samples&sz=640x480&cust_params=sample_ct%3Dlinear&ciu_szs=300x250%2C728x90&gdfp_req=1&output=vast&unviewed_position_start=1&env=vp&impl=s&correlator='
    adsRequest.linearAdSlotWidth = 640
    adsRequest.linearAdSlotHeight = 360
    adsRequest.nonLinearAdSlotWidth = 640
    adsRequest.nonLinearAdSlotHeight = 150

    adsLoader.requestAds(adsRequest)

    return () => {
      if (adsLoader) {
        adsLoader.destroy()
      }
    }
  }, [onAdComplete, onAdError])

  return (
    <div className="flex flex-col items-center space-y-4">
      <div
        ref={adContainerRef}
        className="relative w-full max-w-2xl bg-black rounded-lg overflow-hidden"
        style={{ aspectRatio: '16/9' }}
      >
        <video
          ref={videoRef}
          className="w-full h-full"
          playsInline
        />
      </div>
      <p className="text-gray-600 text-center">
        광고가 자동으로 재생됩니다. 광고 시청 완료 후 검사가 시작됩니다.
      </p>
    </div>
  )
}
