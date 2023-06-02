import asyncio
import os

from tinkoff.invest import (
    AsyncClient,
    CandleInstrument,
    MarketDataRequest,
    SubscribeCandlesRequest,
    SubscriptionAction,
    SubscriptionInterval,
)

TOKEN = 't.b7eKSJEp3fpSiiv4mVt4fWwKIxaMHM1lDMtpGsPTeyl850b9Y4MluXYv-EQrj1vEu7QfkNwqGqGPfTW9N6EvTg'


async def main():
    async def request_iterator():
        yield MarketDataRequest(
            subscribe_candles_request=SubscribeCandlesRequest(
                subscription_action=SubscriptionAction.SUBSCRIPTION_ACTION_SUBSCRIBE,
                instruments=[
                    CandleInstrument(
                        figi="BBG006L8G4H1",
                        interval=SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE,
                    )
                ],
            )
        )
        while True:
            await asyncio.sleep(1)

    async with AsyncClient(TOKEN) as client:
        async for marketdata in client.market_data_stream.market_data_stream(
            request_iterator()
        ):
            '''print(f'#YNDX Volume: {marketdata.candle.volume}, Close: {marketdata.candle.close}, Time: {marketdata.candle.time}' )'''
            print(marketdata)
            break


if __name__ == "__main__":
    asyncio.run(main())
