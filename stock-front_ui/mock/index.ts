import authMock from './auth'
import dashboardMock from './dashboard'
import stocksMock from './stocks'
import selectionMock from './selection'
import boardsMock from './boards'
import jobsMock from './jobs'
import coverageMock from './coverage'
import backfillMock from './backfill'
import watchlistMock from './watchlist'

export default [
  ...authMock,
  ...dashboardMock,
  ...stocksMock,
  ...selectionMock,
  ...boardsMock,
  ...jobsMock,
  ...coverageMock,
  ...backfillMock,
  ...watchlistMock,
]
