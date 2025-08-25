-- ===================================================================
-- Additional Information Required Process Logic
-- 2025.04.29	RITM0063559		PB		34024 implementation
-- =================================================================

DECLARE @ResultCode INT;
DECLARE @PreviousFolderStatusCode INT;
DECLARE @InitiatedProcessRSN INT;
DECLARE @lastStatusCode INT;
DECLARE @originalAssignedUser VARCHAR(50);
DECLARE @originalTeamCode VARCHAR(50);
DECLARE @InitiatingUser VARCHAR(50);
DECLARE @Today               DATETIME = GETDATE();

SELECT @ResultCode = ResultCode
FROM FolderProcessAttempt
WHERE ProcessRSN = @ProcessRSN AND AttemptRSN = @AttemptRSN;

-- ===================
-- RESULT CODE 1220 - In Progress
-- ===================
IF @ResultCode = 1220
BEGIN
	---Update Process Status to 18040 (In Progress)]
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 18040,  --> in progress
		@EndDateIsNULL=1; 

END

-- ===================
-- RESULT CODE 23008 - Request Info
-- ===================
IF @ResultCode = 23008
BEGIN
    -- Validate
	DECLARE @AttemptComment NVARCHAR(MAX);

	-- Retrieve the attempt comment
	SELECT @AttemptComment = attemptcomment 
	FROM folderprocessattempt 
	WHERE processRSN = @ProcessRSN And AttemptRSN = @AttemptRSN;
	
	IF TRIM(ISNULL(@AttemptComment, '')) = ''
	BEGIN
		RAISERROR('Attempt Comment is required to request additional information.', 16, 1);
		RETURN;
	END

    EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 23001,             -- Additional Info Req.
		@AssignedUserIsNULL = 1,         -- Clear AssignedUser
		@TeamCodeIsNULL = 1;             -- Clear TeamCode


    ---Update Folder Status 
	EXEC dbo.cp_UpdateFolder 
		@FolderRSN = @FolderRSN, 
		@StatusCode = 2003;			--pending additional info 

    -- Email applicant with the attempt comment (template ID 202)
    EXEC dbo.Send_Templated_Mail_Folder 202, @FolderRSN, NULL, NULL, NULL, NULL, NULL;		-- template to be filled out 

END

-- ===================
-- RESULT CODE 23005 - Information Received
-- ===================
IF @ResultCode = 23005
BEGIN
	-- Get the initiating user from the FolderProcess table
	SELECT @InitiatingUser = AssignedUser
	FROM FolderProcess
	WHERE ProcessRSN = @ProcessRSN;

    ---Update Process Status 
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 23011,
		@AssignedUser = @InitiatingUser,
		@AssignedUserIsNULL = 0;		--additonal info submitted.

END

-- ===================
-- RESULT CODE 23004 - Completed
-- ===================
IF @ResultCode = 23004
BEGIN
    ---Update Process Status 
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 2,
		@EndDate = @Today;		--closed

    -- Reset Folder status to the last one prior to Additional Info process
    --SELECT @PreviousFolderStatusCode = dbo.cf_GetPreviousFolderStatus(@FolderRSN, 2003)

    /*IF @PreviousFolderStatusCode IS NOT NULL
    BEGIN
        UPDATE Folder SET StatusCode = @PreviousFolderStatusCode
        WHERE FolderRSN = @FolderRSN;
    END

    -- Restore initiated process to its last status before Additional Info
    SELECT @InitiatedProcessRSN = Reference
    FROM FolderProcess
    WHERE ProcessRSN = @ProcessRSN;

    IF @InitiatedProcessRSN IS NOT NULL
    BEGIN
        SELECT @lastStatusCode = StatusCode
        FROM FolderProcess WHERE ProcessRSN = @InitiatedProcessRSN;

        IF @lastStatusCode = 23000 -- Additional Info Required
        BEGIN
            SELECT TOP 1 @lastStatusCode = StatusCode, @originalAssignedUser = AssignedUser, @originalTeamCode = TeamCode
            FROM LogFolderProcess
            WHERE ProcessRSN = @InitiatedProcessRSN AND StatusCode <> 23000
            ORDER BY LogDate DESC;
        END
        ELSE
        BEGIN
            SELECT TOP 1
                @lastStatusCode = l0.StatusCode,
                @originalAssignedUser = l0.AssignedUser,
                @originalTeamCode = l0.TeamCode
            FROM LogFolderProcess l1
            JOIN LogFolderProcess l0 ON l1.ProcessRSN = @InitiatedProcessRSN AND l0.ProcessRSN = @InitiatedProcessRSN
            WHERE l1.StatusCode = 23000
              AND l1.LogDate > l0.LogDate
              AND l0.StatusCode <> 23000
            ORDER BY l0.LogDate DESC;
        END

        IF @lastStatusCode IS NOT NULL
        BEGIN
            UPDATE FolderProcess
            SET
                StatusCode = @lastStatusCode,
                TeamCode = @originalTeamCode,
                AssignedUser = @originalAssignedUser,
                StampDate = GETDATE(),
                StampUser = '23751_23004'
            WHERE ProcessRSN = @InitiatedProcessRSN;
        END
    END*/

END

-- ===================
-- RESULT CODE 950 - Cancelled
-- ===================
IF @ResultCode = 950
BEGIN
    -- Validate cancellation reason using the function
	IF dbo.cf_GetProcessInfo(@ProcessRSN, 34200) IS NULL
	BEGIN
		RAISERROR('Cancellation reason is required.', 16, 1);
		RETURN;
	END

    ---Update Process Status 
	EXEC dbo.cp_UpdateFolderProcess 
		@ProcessRSN = @ProcessRSN, 
		@StatusCode = 15,		--	cancelled
		@EndDate = @Today;

    ---Update Folder Status 
	EXEC dbo.cp_UpdateFolder 
		@FolderRSN = @FolderRSN, 
		@StatusCode = 4,
		@FinalDate = @Today;--	cancelled

    -- Send cancellation email
    EXEC dbo.Send_Templated_Mail_Folder 97, @FolderRSN, NULL, NULL, NULL, NULL, NULL;

END
