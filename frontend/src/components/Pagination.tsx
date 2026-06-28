import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export default function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null

  const BLOCK_SIZE = 5
  // Calculate current block start and end pages
  const currentBlock = Math.floor((currentPage - 1) / BLOCK_SIZE)
  const startPage = currentBlock * BLOCK_SIZE + 1
  const endPage = Math.min(startPage + BLOCK_SIZE - 1, totalPages)

  const pages = []
  for (let i = startPage; i <= endPage; i++) {
    pages.push(i)
  }

  const handlePrevBlock = () => {
    onPageChange(Math.max(1, startPage - BLOCK_SIZE))
  }

  const handleNextBlock = () => {
    onPageChange(Math.min(totalPages, startPage + BLOCK_SIZE))
  }

  return (
    <div className="flex justify-center items-center gap-1.5 mt-8">
      {/* First Page */}
      <button
        onClick={() => onPageChange(1)}
        disabled={currentPage === 1}
        className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="First page"
      >
        <ChevronsLeft className="w-4 h-4" />
      </button>

      {/* Previous Block */}
      <button
        onClick={handlePrevBlock}
        disabled={startPage === 1}
        className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="Previous 5 pages"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {/* Pages */}
      <div className="flex gap-1 mx-2">
        {pages.map((p) => (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`w-8 h-8 flex items-center justify-center rounded-md text-sm font-medium transition-colors focus:outline-none ${
              currentPage === p
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Next Block */}
      <button
        onClick={handleNextBlock}
        disabled={endPage === totalPages}
        className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="Next 5 pages"
      >
        <ChevronRight className="w-4 h-4" />
      </button>

      {/* Last Page */}
      <button
        onClick={() => onPageChange(totalPages)}
        disabled={currentPage === totalPages}
        className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="Last page"
      >
        <ChevronsRight className="w-4 h-4" />
      </button>
    </div>
  )
}
