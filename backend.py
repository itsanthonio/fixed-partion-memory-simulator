from typing import List, Dict, Any, Optional, Literal

class MemoryAllocator:
    """
    Handles memory allocation logic for the memory simulator.
    This class is stateless and provides pure functions for memory allocation.
    """
    
    @staticmethod
    def first_fit(memory: List[Dict[str, Any]], job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find the first block that can fit the job using first-fit strategy.
        Returns the allocated block or None if no block can fit.
        """
        for block in memory:
            if block['status'] == 'free' and block['size'] >= job['size']:
                return block
        return None
    
    @staticmethod
    def best_fit(memory: List[Dict[str, Any]], job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find the best fitting block for the job using best-fit strategy.
        Returns the allocated block or None if no block can fit.
        """
        best_block = None
        min_waste = float('inf')
        
        for block in memory:
            if block['status'] == 'free' and block['size'] >= job['size']:
                waste = block['size'] - job['size']
                if waste < min_waste:
                    min_waste = waste
                    best_block = block
        
        return best_block
    
    @classmethod
    def allocate_memory(
        cls,
        memory: List[Dict[str, Any]],
        job: Dict[str, Any],
        strategy: Literal['first_fit', 'best_fit'] = 'first_fit'
    ) -> Dict[str, Any]:
        """
        Allocate memory for a job using the specified strategy.
        Returns a dictionary containing:
        - success: bool indicating if allocation was successful
        - memory: updated memory state
        - job: updated job state
        - message: status message
        """
        
        # Find a suitable block
        if strategy == 'first_fit':
            block = cls.first_fit(memory, job)
        else:  # best_fit
            block = cls.best_fit(memory, job)
        
        if block is None:
            return {
                'success': False,
                'memory': memory,
                'job': job,
                'message': f"No suitable block found for job {job.get('stream', '?')} of size {job['size']}"
            }
        
        # Allocate the block
        block_index = memory.index(block)
        memory[block_index] = {
            **block,
            'status': 'occupied',
            'job': job.copy(),
            'internal_fragmentation': block['size'] - job['size'],
            'usage_count': block.get('usage_count', 0) + 1  
        }
        
        # Update job status
        updated_job = job.copy()
        updated_job['status'] = 'running'
        updated_job['allocated_block'] = block['block']
        
        return {
            'success': True,
            'memory': memory,
            'job': updated_job,
            'message': f"Job {job.get('stream', '?')} allocated to Block {block['block']} "
                      f"(waste={block['size'] - job['size']})"
        }
    
    @staticmethod
    def deallocate_memory(memory: List[Dict[str, Any]], block_id: int) -> Dict[str, Any]:
        """
        Deallocate a memory block.
        Returns the updated memory state and the deallocated job.
        """
        
        for i, block in enumerate(memory):
            if block['block'] == block_id and block['status'] == 'occupied':
                
                usage_count = block.get('usage_count', 0)
                job = block['job']
                memory[i] = {
                    'block': block['block'],
                    'size': block['size'],
                    'status': 'free',
                    'job': None,
                    'internal_fragmentation': 0,
                    'usage_count': usage_count  
                }
                
                return {
                    'success': True,
                    'memory': memory,
                    'message': f"Block {block_id} has been freed"
                }
        
        return {
            'success': False,
            'memory': memory,
            'job': None,
            'message': f"Block {block_id} is not allocated or doesn't exist"
        }
