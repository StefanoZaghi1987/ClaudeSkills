# Meeting Room Booking System — Requirements

## §1 Purpose

The system lets office staff book meeting rooms, manage the room catalog, and report on usage.

## §2 Actors

- **Employee**: any staff member who books rooms
- **Facility Administrator**: manages rooms and equipment
- **Office Manager**: reviews usage and approves exceptions

## §3 Functional Requirements

### §3.1 Booking

The system shall allow employees to search rooms by capacity, equipment, and time slot. Employees must be authenticated. A booking can be made up to 30 days in advance.

### §3.2 Cancellation

An employee can cancel their own booking. The room becomes immediately available to others.

### §3.3 Booking Window

No booking may be placed more than 14 days in advance.

### §3.4 Recurring Bookings

An employee can create a weekly recurring booking. Each occurrence is a separate booking and follows the same rules.

### §3.5 Room Management

The facility administrator can add, modify, and deactivate rooms, including capacity, equipment list, floor, and photo.

### §3.6 Check-in

For rooms marked "check-in required", the booking is released automatically if the employee does not check in within 15 minutes of the start time.

### §3.7 Usage Reports

The office manager can generate monthly usage reports per room and per floor, showing occupancy rate and no-show count.

### §3.8 Notifications

The system sends a confirmation email when a booking is made and a reminder 24 hours before the start time.

## §4 Non-Functional Requirements

- Search response time under 2 seconds
- Availability 99.5% during office hours
- All actions logged for audit

## §5 Open Points

- The penalty for repeated no-shows is not yet defined.
