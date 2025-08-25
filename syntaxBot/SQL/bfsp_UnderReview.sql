-- ==============================================================
-- Under Review Process Logic
-- 2025.04.10	RITM0063559		PB		34022 implementation
-- ===============================================================

DECLARE @ResultCode INT;
DECLARE @NewProcessRSN INT;
DECLARE @AssignedUserCurrent VARCHAR(50);
DECLARE @TeamCodeCurrent VARCHAR(50);

SELECT 
	@ResultCode = ResultCode
FROM FolderProcessAttempt
WHERE ProcessRSN = @ProcessRSN AND AttemptRSN = @AttemptRSN;

-- Get current AssignedUser and TeamCode from the active process
SELECT 
    @AssignedUserCurrent = AssignedUser,
    @TeamCodeCurrent     = TeamCode
FROM FolderProcess
WHERE ProcessRSN = @ProcessRSN;


-- ===================
-- RESULT CODE 905 CANCELLED
-- ===================
IF @ResultCode = 950
BEGIN
    -- Validate that "Cancelled Reason" or "Denied Reason" is filled
    IF dbo.cf_ProcessInfo_Process(@ProcessRSN, 34200) IS NULL											--just cancelled reason needed 
    BEGIN
        RAISERROR('a Cancelled or Denied reason must be present before cancelling the application.', 16, 1);
        RETURN;
    END;

    -- Update Folder Status
    EXEC dbo.cp_UpdateFolder 
        @FolderRSN = @FolderRSN, 
        @StatusCode = 4;			-- cancelled

    -- Update Process Status
    EXEC dbo.cp_UpdateFolderProcess 
        @ProcessRSN = @ProcessRSN, 
        @StatusCode = 2;

    -- Email applicant the application has been cancelled
    EXEC dbo.Send_Templated_Mail_Folder 97, @FolderRSN, NULL, NULL, NULL, NULL, NULL;
END

-- ===================
-- RESULT CODE 1220 IN PROGRESS
-- ===================
IF @ResultCode = 1220
BEGIN

    ---Update Process Status 
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 18040,	-- In Progress
		@EndDateIsNULL = 1;  

    ---Update Folder Status 
	EXEC dbo.cp_UpdateFolder 
		@FolderRSN = @FolderRSN, 
		@StatusCode = 2004; -- Under Review	
END

-- ===================
-- RESULT CODE 1 APPROVED
-- ===================
IF @ResultCode = 1
BEGIN
	-- Update Process Status (Closed)
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 2; -- Closed

	-- Update Folder Status (Ready for Payment)
	EXEC dbo.cp_UpdateFolder 
		@FolderRSN = @FolderRSN, 
		@StatusCode = 2008;

	-- Process Right-of-Way fees
    EXEC dbo.[cp_ProcessFees]
        @FolderRSN = @FolderRSN,
        @AutoBill = 1;

END

-- ===================
-- RESULT CODE ON HOLD
-- ===================
IF @ResultCode = 2025
BEGIN

	---Update Process Status 
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 7,				-- On Hold
		@EndDateIsNULL = 1;				-- This explicitly nulls out the EndDate

    ---Update Folder Status 
	EXEC dbo.cp_UpdateFolder 
		@FolderRSN = @FolderRSN,	
		@StatusCode = 1000;				-- On Hold

	-- Keeps the process assigned to the team and user --> Should already be doing this 

END

-- ===================
-- RESULT CODE 24051 ADDITONAL INFO REQ
-- ===================
IF @ResultCode = 24051
BEGIN
	---Update Process Status 
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@AssignedUserIsNULL = 1,		-- Removes assigned team and user from this process
		@TeamCodeIsNULL     = 1,
		@SignoffUser        = NULL,          
		@ScheduleDate       = NULL,          
		@EndDate            = NULL,    
		@StatusCode = 23001;			-- Pending additonal information

    ---Update Folder Status 
	EXEC dbo.cp_UpdateFolder 
		@FolderRSN = @FolderRSN, 
		@StatusCode = 2004; -- Under Review (NOT CHNGING FOR SOME REASON)

	-- Inserts 'Additional Information Required' process --> Default assign: Team and named user who initiated from this process {Waiting on this}
	EXEC dbo.cp_InsertFolderProcess
      @FolderRSN      = @FolderRSN,
      @ProcessCode    = 34024,                -- Additional Information Required
      @ScheduleDate   = NULL,                 -- Let the procedure calculate it
      @StatusCode     = 1,                     -- Open
      @UserId         = @UserId,             -- Person initiating
      @AssignedUser   = @AssignedUserCurrent,  -- Keep same user as original process
      @TeamCode       = @TeamCodeCurrent,      -- Keep same team as original process
      @NewProcessRSN  = @NewProcessRSN OUTPUT;
END

-- ===================
-- RESULT CODE 3075 DENIED
-- ===================
IF @ResultCode = 3075
BEGIN

	-- Validate
	IF TRIM(ISNULL(dbo.cf_ProcessInfo_Process(@ProcessRSN, 34205), '')) = ''
	BEGIN
		RAISERROR('Denied Reason must be provided (ProcessInfo 34205).', 16, 1);
		RETURN;
	END

    --  Update Process Status to Closed
    EXEC dbo.cp_UpdateFolderProcess 
        @ProcessRSN = @ProcessRSN, 
        @StatusCode = 2;

    --  Update Folder Status to Denied
    EXEC dbo.cp_UpdateFolder 
        @FolderRSN = @FolderRSN, 
        @StatusCode = 30070;

    --  Send Denied Notification Email to Applicant
    EXEC dbo.Send_Templated_Mail_Folder 98, @FolderRSN, NULL, NULL, NULL, NULL, NULL;
END